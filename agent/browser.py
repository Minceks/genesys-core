from typing import Any

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    sync_playwright,
)

from .daytona_workspace import get_workspace


# ============================================================
# BROWSER CONFIG
# ============================================================

VIEWPORT_WIDTH = 1280
VIEWPORT_HEIGHT = 800

DEFAULT_TIMEOUT_MS = 10000


# ============================================================
# BROWSER SESSION
# ============================================================

class BrowserSession:
    """
    Persistent Playwright browser session for one GeneSys project.

    The application itself runs inside Daytona.
    Playwright connects to the signed external preview URL.
    """

    def __init__(
        self,
        project_id: str,
    ) -> None:

        self.project_id = (
            str(project_id).strip()
            or "genesys-project"
        )

        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

        self.console_messages: list[dict[str, Any]] = []

    # ========================================================
    # START
    # ========================================================

    def start(self) -> Page:

        if self.page is not None:
            return self.page

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

        self.browser = (
            self.playwright.chromium.launch(
                headless=True,
            )
        )

        self.context = (
            self.browser.new_context(
                viewport={
                    "width": VIEWPORT_WIDTH,
                    "height": VIEWPORT_HEIGHT,
                },
            )
        )

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

    # ========================================================
    # CONSOLE
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

            # Keep the session bounded.
            if len(self.console_messages) > 200:
                self.console_messages = (
                    self.console_messages[-200:]
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

    def screenshot(
        self,
    ) -> dict[str, Any]:

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

    def get_console(
        self,
    ) -> dict[str, Any]:

        self.start()

        return {
            "status": "success",
            "projectId": self.project_id,
            "messages": list(
                self.console_messages
            ),
        }

    # ========================================================
    # CLICK
    # ========================================================

    def click(
        self,
        selector: str,
    ) -> dict[str, Any]:

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

    def type(
        self,
        selector: str,
        text: str,
    ) -> dict[str, Any]:

        page = self.start()

        page.locator(
            selector
        ).fill(text)

        return {
            "status": "success",
            "projectId": self.project_id,
            "action": "type",
            "selector": selector,
        }

    # ========================================================
    # KEYPRESS
    # ========================================================

    def keypress(
        self,
        key: str,
    ) -> dict[str, Any]:

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
    # STOP
    # ========================================================

    def stop(
        self,
    ) -> None:

        if self.context is not None:
            self.context.close()

        if self.browser is not None:
            self.browser.close()

        if self.playwright is not None:
            self.playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

        self.console_messages.clear()


# ============================================================
# SESSION CACHE
# ============================================================

_sessions: dict[
    str,
    BrowserSession,
] = {}


def get_browser(
    project_id: str = "genesys-project",
) -> BrowserSession:

    key = (
        str(project_id).strip()
        or "genesys-project"
    )

    if key not in _sessions:
        _sessions[key] = BrowserSession(
            key
        )

    return _sessions[key]


def stop_browser(
    project_id: str = "genesys-project",
) -> dict[str, Any]:

    key = (
        str(project_id).strip()
        or "genesys-project"
    )

    session = _sessions.get(
        key
    )

    if session is not None:
        session.stop()

    return {
        "status": "success",
        "projectId": key,
    }