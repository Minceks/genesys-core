from concurrent.futures import ThreadPoolExecutor
import asyncio
from types import SimpleNamespace

from agent import browser


def test_two_projects_repeat_and_change_calling_threads(monkeypatch):
    monkeypatch.setattr(browser, "get_workspace", lambda project: SimpleNamespace(
        start_preview=lambda: {"url": f"data:text/html,<h1>{project}</h1>"},
    ))
    projects = ["lifecycle-test-a", "lifecycle-test-b"]
    try:
        first, second = [browser.get_browser(project) for project in projects]
        assert first.screenshot()["status"] == "success"
        assert second.screenshot()["status"] == "success"
        assert first._worker_thread_id != second._worker_thread_id
        with ThreadPoolExecutor(max_workers=2) as callers:
            results = list(callers.map(lambda session: session.get_console(), [first, second]))
        assert all(result["hasRuntimeErrors"] is False for result in results)
        async def verify_from_async_caller():
            assert second.get_console()["hasRuntimeErrors"] is False
        asyncio.run(verify_from_async_caller())
        assert first.screenshot()["status"] == "success"
        browser.stop_browser(projects[0])
        assert browser.get_browser(projects[0]).screenshot()["status"] == "success"
    finally:
        for project in projects:
            browser.stop_browser(project)
