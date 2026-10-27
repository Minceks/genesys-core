import json
from types import SimpleNamespace

from playwright.sync_api import sync_playwright

from agent.functional_verification import target, observed_control_target, verify_functions
from agent.observed_targets import active_dialog_target, canonical_name


def test_typography_and_dialog_scope_resolve_only_observed_unique_matches():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content('''<h2>Hand\u2011Crank Tactical Lantern</h2>
                <input aria-label="Quantity for Hand\u2011Crank Tactical Lantern">
                <button aria-label="Cart with 2 items">Cart</button>
                <aside role="dialog" aria-label="Cart"><p>Hand\u2011Crank Tactical Lantern</p></aside>''')
            assert target(page, {'by': 'label', 'name': 'Quantity for Hand Crank Tactical Lantern'}).count() == 1
            assert target(page, {'by': 'text', 'name': 'Hand\ncrank Tactical Lantern'}).count() == 2
            scoped = active_dialog_target(page, {'by': 'text', 'name': 'Hand Crank Tactical Lantern'}, target)
            assert scoped is not None and scoped.count() == 1
            assert observed_control_target(page, {'by': 'role', 'role': 'button', 'name': 'Cart with 0 items'}) is not None
            assert target(page, {'by': 'role', 'role': 'button', 'name': 'Cart with 0 items'}).count() == 0
            # A badge assertion is never silently changed to the current count.
            page.set_content('<h2>Model-A</h2><h2>Model A</h2><button>Remove item 2</button>')
            assert target(page, {'by': 'text', 'name': 'Model\u2011A'}).count() == 0
            assert observed_control_target(page, {'by': 'role', 'role': 'button', 'name': 'Remove item 0'}) is None
            assert canonical_name('Item 12') != canonical_name('Item 2')
            assert canonical_name('-129') != canonical_name('129')
        finally:
            browser.close()


def test_image_control_state_is_rejected_before_browser_actions():
    plan = {'requirements': [{'id': 'image', 'name': 'View product illustration'}],
            'checks': [{'name': 'Incorrect image assertion', 'covers': ['image'], 'steps': [
                {'action': 'attribute', 'target': {'by': 'role', 'role': 'img', 'name': 'Lantern'},
                 'attribute': 'aria-pressed', 'value': 'true'}]}]}
    provider = SimpleNamespace(generate=lambda *_: SimpleNamespace(text=json.dumps(plan)))
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.route('http://verification.test/**', lambda route: route.fulfill(
                body='<svg role="img" aria-label="Lantern"></svg>', content_type='text/html'))
            page.goto('http://verification.test/')
            result = verify_functions(page, 'View product illustration', provider, attempt=1)
            assert not result['testedInteractions']
            assert 'images do not expose control state' in result['unverifiedCore'][0]
            assert '_verifiedPlan' not in result
        finally:
            browser.close()


def test_css_text_transform_does_not_corrupt_status_or_action_selectors():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content('<style>span,button{text-transform:uppercase}</style><span>pending</span><button>Confirm order</button>')
            assert page.locator('span').inner_text() == 'PENDING'
            assert target(page, {'by':'text','name':'pending','exact':True}).count() == 1
            assert target(page, {'by':'text','name':'PENDING','exact':True}).count() == 1
            assert target(page, {'by':'role','role':'button','name':'Confirm order','exact':True}).count() == 1
        finally:
            browser.close()
