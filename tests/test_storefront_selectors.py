import pytest
from playwright.sync_api import sync_playwright
from agent.functional_verification import target


@pytest.fixture
def page():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.set_content('''<main>
          <article><h2>Fixture Kit</h2>
            <button aria-label="View details for Fixture Kit" onclick="this.dataset.clicked='yes'">View</button>
            <button aria-label="Add 1 Fixture Kit to cart" onclick="this.dataset.clicked='yes'">Add to cart — $10.00</button>
          </article>
          <article><h2>Other Kit</h2>
            <button aria-label="View details for Other Kit">View</button>
            <button aria-label="Add 1 Other Kit to cart">Add to cart — $20.00</button>
          </article></main>''')
        yield page
        browser.close()


@pytest.mark.parametrize('name,exact,accessible', [
    ('View', True, 'View details for Fixture Kit'),
    ('Add to cart', False, 'Add 1 Fixture Kit to cart'),
])
def test_visible_card_actions_survive_descriptive_accessibility_labels(page, name, exact, accessible):
    locator = target(page, {'by': 'text', 'name': name, 'exact': exact, 'withinText': 'Fixture Kit'})
    assert locator.count() == 1
    locator.click()
    assert page.get_by_role('button', name=accessible, exact=True).get_attribute('data-clicked') == 'yes'
    assert page.get_by_role('button', name='View details for Other Kit', exact=True).get_attribute('data-clicked') is None


def test_duplicate_actions_in_same_card_are_rejected(page):
    page.locator('article').first.evaluate("el => el.append(el.querySelector('button').cloneNode(true))")
    with pytest.raises(ValueError, match='uniquely identified'):
        target(page, {'by': 'text', 'name': 'View', 'exact': True, 'withinText': 'Fixture Kit'})
