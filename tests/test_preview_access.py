import pytest
from playwright.sync_api import sync_playwright
from agent.preview_access import check_preview_document,PreviewAccessBlocked


def test_network_warning_is_not_treated_as_a_broken_generated_game():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            page=browser.new_page()
            page.set_content('<h1>UZMANĪBU!</h1><p>Antivīruss Plus: piekļuve ir ierobežota. www.bite.lv</p><button>Turpināt</button>')
            with pytest.raises(PreviewAccessBlocked,match='Source is preserved'):check_preview_document(page)
            assert page.get_by_role('button',name='Turpināt').is_visible()
            page.set_content('<canvas aria-label="Playfield"></canvas><button>Start game</button>')
            check_preview_document(page)
        finally:browser.close()
