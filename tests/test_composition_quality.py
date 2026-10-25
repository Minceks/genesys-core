from agent.design_execution import design_execution
from agent.visual_quality import assess_visual_quality, SNAPSHOT_SCRIPT
from tests.test_visual_quality import snapshot
from playwright.sync_api import sync_playwright
import pytest


@pytest.mark.parametrize('kind', ['store', 'portfolio', 'website', 'app', 'dashboard', 'game'])
def test_each_product_has_an_implementable_composition_handoff(kind):
    brief = design_execution({'productType': kind})['compositionBrief']
    assert brief['firstScreen'] and brief['innerExperience']
    assert len(brief['sectionSequence']) == 3
    assert 'stylesheet' in brief['implementationDeliverables'][0]
    if kind in {'app', 'dashboard', 'game'}:
        assert 'storefront' not in brief['direction'].lower()


def plain(**changes):
    return snapshot(width=1280, brandVisual=True, favicon=True, titleSize=32,
                    contentLayout=False, firstScreenMediaRatio=0, **changes)


def test_styled_header_alone_does_not_satisfy_body_composition():
    result = assess_visual_quality([plain()], public_website=True)
    assert any('plain document flow' in item for item in result['issues'])


def test_expressive_text_led_site_needs_no_forced_images():
    data = plain(); data['titleSize'] = 64
    assert assess_visual_quality([data], public_website=True)['status'] == 'success'
    assert assess_visual_quality([plain()], public_website=True, allow_unstyled=True)['status'] == 'success'
    assert assess_visual_quality([plain()], public_website=False)['status'] == 'success'


def test_real_browser_distinguishes_navigation_from_content_and_small_icons():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={'width':1280,'height':800})
            page.set_content('<nav style="display:flex"><a>Home</a><a>About</a></nav><main><h1>Our products</h1><svg width="16" height="16"><circle r="4"/></svg><p>Browse the catalog.</p></main>')
            data = page.evaluate(SNAPSHOT_SCRIPT)
            assert data['composedLayout'] is True
            assert data['contentLayout'] is False
            assert data['firstScreenMediaRatio'] < .08
            assert any('plain document flow' in issue for issue in assess_visual_quality([data], public_website=True)['issues'])
            page.locator('main').evaluate("el=>el.style.display='grid'")
            assert page.evaluate(SNAPSHOT_SCRIPT)['contentLayout'] is True
        finally:
            browser.close()
