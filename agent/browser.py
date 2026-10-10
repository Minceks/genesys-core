from typing import Any
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from .daytona_workspace import get_workspace
from .visual_quality import SNAPSHOT_SCRIPT, assess_visual_quality


# ============================================================
# BROWSER CONFIG
# ============================================================

VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 800

DEFAULT_TIMEOUT_MS = 10000


def browser_thread(method):
    """Keep each project's sync Playwright driver on its own dedicated thread."""
    @wraps(method)
    def dispatch(self, *args, **kwargs):
        if threading.get_ident() == self._worker_thread_id:
            return method(self, *args, **kwargs)

        def run():
            self._worker_thread_id = threading.get_ident()
            return method(self, *args, **kwargs)

        return self._executor.submit(run).result()
    return dispatch


# ============================================================
# BROWSER SESSION
# ============================================================

class BrowserSession:
    """
    Persistent Playwright browser session for one GeneSys project.

    The application itself runs inside Daytona.
    Playwright connects to the signed external preview URL.

    Browser sessions are recoverable:
    if Playwright/page/browser dies, GeneSys recreates the session.

    All operations run on a dedicated thread for this project so
    different callers and projects cannot share a Playwright event loop.
    """

    def __init__(
        self,
        project_id: str,
    ) -> None:

        self.project_id = (
            str(project_id).strip()
            or "genesys-project"
        )
        self._worker_thread_id: int | None = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="genesys-browser")

        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

        self.console_messages: list[dict[str, Any]] = []
        self.network_errors: list[dict[str, Any]] = []

        # Playwright sync objects are thread-sensitive.
        self.owner_thread_id: int | None = None

    # ========================================================
    # SESSION HEALTH
    # ========================================================

    def _is_alive(self) -> bool:
        """
        Check whether the current Playwright session is still usable.
        """

        if (
            self.playwright is None
            or self.browser is None
            or self.context is None
            or self.page is None
        ):
            return False

        # Playwright sync API objects must stay on the thread
        # where they were created.
        current_thread_id = threading.get_ident()

        if (
            self.owner_thread_id is not None
            and self.owner_thread_id != current_thread_id
        ):
            return False

        try:
            if not self.browser.is_connected():
                return False

            if self.page.is_closed():
                return False

            # Lightweight operation to catch dead connections.
            _ = self.page.url

            return True

        except Exception:
            return False

    # ========================================================
    # START
    # ========================================================

    @browser_thread
    def start(self) -> Page:
        """
        Start or reuse the browser session and navigate to the
        current Daytona preview URL.
        """

        current_thread_id = threading.get_ident()

        # Reuse a healthy session on the same thread.
        if self._is_alive():
            return self.page  # type: ignore[return-value]

        # A stale, dead, or thread-owned-by-another-thread session
        # must be destroyed before recreating it.
        self._cleanup_session()

        workspace = get_workspace(
            self.project_id
        )

        preview = workspace.start_preview()

        url = preview.get("url")

        if not url:
            raise RuntimeError(
                "Daytona preview did not return a URL."
            )

        self.playwright = sync_playwright().start()

        try:
            self.browser = (
                self.playwright.chromium.launch(
                    headless=True,
                )
            )

            # Daytona preview URLs use dynamically generated HTTPS
            # proxy certificates. Playwright must ignore certificate
            # validation errors for these sandbox preview URLs.
            self.context = (
                self.browser.new_context(
                    viewport={
                        "width": VIEWPORT_WIDTH,
                        "height": VIEWPORT_HEIGHT,
                    },
                    ignore_https_errors=True,
                )
            )

            self.owner_thread_id = current_thread_id

            self.page = self.context.new_page()

            self.page.set_default_timeout(
                DEFAULT_TIMEOUT_MS
            )

            self._attach_console_listener()

            self.page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=30000,
            )

            return self.page

        except Exception:
            # If startup itself fails, make sure no partially-created
            # Playwright objects remain cached.
            self._cleanup_session()
            raise

    # ========================================================
    # CONSOLE LISTENER
    # ========================================================

    def _attach_console_listener(
        self,
    ) -> None:

        if self.page is None:
            return

        def handle_console(message) -> None:

            self.console_messages.append(
                {
                    "type": message.type,
                    "text": message.text,
                }
            )

            if len(self.console_messages) > 200:
                self.console_messages = (
                    self.console_messages[-200:]
                )

        def handle_response(response) -> None:
            if response.status >= 400:
                self.network_errors.append(
                    {
                        "status": response.status,
                        "url": response.url,
                        "method": response.request.method,
                        "resourceType": response.request.resource_type,
                    }
                )

                if len(self.network_errors) > 200:
                    self.network_errors = (
                        self.network_errors[-200:]
                    )

        self.page.on(
            "response",
            handle_response,
        )

        self.page.on(
            "console",
            handle_console,
        )

        def handle_page_error(error) -> None:

            self.console_messages.append(
                {
                    "type": "pageerror",
                    "text": str(error),
                }
            )

            if len(self.console_messages) > 200:
                self.console_messages = (
                    self.console_messages[-200:]
                )

        self.page.on(
            "pageerror",
            handle_page_error,
        )

    # ========================================================
    # SCREENSHOT
    # ========================================================

    @browser_thread
    def screenshot(
        self,
    ) -> dict[str, Any]:

        page = self.start()

        try:
            image = page.screenshot(
                type="png",
                full_page=True,
            )

        except Exception:
            # The page may have died between start() and screenshot().
            # Recreate the browser session and retry once.
            self._cleanup_session()

            page = self.start()

            image = page.screenshot(
                type="png",
                full_page=True,
            )

        return {
            "status": "success",
            "projectId": self.project_id,
            "url": page.url,
            "image": image.hex(),
            "format": "png",
        }

    # ========================================================
    # GET CONSOLE
    # ========================================================

    @browser_thread
    def visual_quality(self, *, allow_unstyled=False) -> dict[str, Any]:
        page = self.start()
        original = page.viewport_size
        snapshots = []
        try:
            for width, height in ((1280, 800), (390, 844)):
                page.set_viewport_size({'width': width, 'height': height})
                page.wait_for_timeout(200)
                snapshots.append(page.evaluate(SNAPSHOT_SCRIPT))
        finally:
            if original:
                page.set_viewport_size(original)
        return assess_visual_quality(snapshots, allow_unstyled=allow_unstyled)

    @browser_thread
    def get_console(
        self,
    ) -> dict[str, Any]:

        self.start()

        messages = list(
            self.console_messages
        )

        page_errors = [
            message
            for message in messages
            if message.get("type") == "pageerror"
        ]

        raw_console_errors = [
            message
            for message in messages
            if message.get("type") == "error"
        ]

        network_errors = list(
            self.network_errors
        )

        def is_logger_delivery_failure(
            error: dict[str, Any],
        ) -> bool:
            url = str(
                error.get("url", "")
            ).split("?", 1)[0].rstrip("/")

            return (
                error.get("status", 0) >= 400
                and str(error.get("method", "")).upper() == "POST"
                and str(error.get("resourceType", "")).lower() == "ping"
                and url.endswith("/browser-console")
            )

        logger_delivery_failures = sum(
            1
            for error in network_errors
            if is_logger_delivery_failure(error)
        )

        console_errors = []
        ignored_console_errors = []

        for error in raw_console_errors:
            text = str(error.get("text", ""))

            if (
                logger_delivery_failures > 0
                and text.startswith("Failed to load resource:")
            ):
                ignored_console_errors.append(error)
                logger_delivery_failures -= 1
            else:
                console_errors.append(error)

        return {
            "status": "success",
            "projectId": self.project_id,
            "messages": messages,
            "pageErrors": page_errors,
            "consoleErrors": console_errors,
            "ignoredConsoleErrors": ignored_console_errors,
            "networkErrors": network_errors,
            "hasRuntimeErrors": bool(
                page_errors or console_errors
            ),
        }

    # ========================================================
    # CLICK
    # ========================================================

    @browser_thread
    def click(
        self,
        selector: str,
    ) -> dict[str, Any]:

        page = self.start()

        try:
            page.locator(
                selector
            ).click()

        except Exception:
            # Retry once with a fresh browser session.
            self._cleanup_session()

            page = self.start()

            page.locator(
                selector
            ).click()

        return {
            "status": "success",
            "projectId": self.project_id,
            "action": "click",
            "selector": selector,
            "url": page.url,
        }

    # ========================================================
    # TYPE
    # ========================================================

    @browser_thread
    def type(
        self,
        selector: str,
        text: str,
    ) -> dict[str, Any]:

        page = self.start()

        try:
            locator = page.locator(selector)

            locator.fill(text)

        except Exception as error:
            message = str(error)

            if (
                "cannot be filled" in message
                or "not editable" in message
                or "waiting for locator" in message
            ):
                return {
                    "status": "error",
                    "success": False,
                    "projectId": self.project_id,
                    "action": "type",
                    "selector": selector,
                    "message": message,
                }

            self._cleanup_session()

            page = self.start()

            page.locator(selector).fill(text)

        return {
            "status": "success",
            "success": True,
            "projectId": self.project_id,
            "action": "type",
            "selector": selector,
        }

    # ========================================================
    # KEYPRESS
    # ========================================================

    @browser_thread
    def keypress(
        self,
        key: str,
    ) -> dict[str, Any]:

        page = self.start()

        try:
            page.keyboard.press(
                key
            )

        except Exception:
            self._cleanup_session()

            page = self.start()

            page.keyboard.press(
                key
            )

        return {
            "status": "success",
            "projectId": self.project_id,
            "action": "keypress",
            "key": key,
        }

    # ========================================================
    # CLEANUP
    # ========================================================

    def _cleanup_session(
        self,
    ) -> None:

        # Close the context first.
        if self.context is not None:
            try:
                self.context.close()
            except Exception:
                pass

        # Then close the browser.
        if self.browser is not None:
            try:
                self.browser.close()
            except Exception:
                pass

        # Finally stop Playwright.
        if self.playwright is not None:
            try:
                self.playwright.stop()
            except Exception:
                pass

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        self.owner_thread_id = None

        self.console_messages.clear()
        self.network_errors.clear()

    # ========================================================
    # STOP
    # ========================================================

    @browser_thread
    def stop(
        self,
    ) -> None:

        self._cleanup_session()


# ============================================================
# SESSION CACHE
# ============================================================

_sessions: dict[
    str,
    BrowserSession,
] = {}
_sessions_lock = threading.Lock()


def get_browser(
    project_id: str = "genesys-project",
) -> BrowserSession:

    key = (
        str(project_id).strip()
        or "genesys-project"
    )

    with _sessions_lock:
        if key not in _sessions:
            _sessions[key] = BrowserSession(key)
        return _sessions[key]


def stop_browser(
    project_id: str = "genesys-project",
) -> dict[str, Any]:

    key = (
        str(project_id).strip()
        or "genesys-project"
    )

    with _sessions_lock:
        session = _sessions.pop(key, None)

    if session is not None:
        try:
            session.stop()
        finally:
            session._executor.shutdown(wait=True)

    return {
        "status": "success",
        "projectId": key,
    }
