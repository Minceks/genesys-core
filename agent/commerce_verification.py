"""Trusted plans for a narrowly recognized browser-local cart/draft contract.

Unknown UI structures or requirements fall through to the general planner. These
are real browser actions, not cached verdicts or a waiver of failed requirements.
"""
import re
from decimal import Decimal


def commerce_plan(page, contract, sources):
    requirements = [item for item in (contract or {}).get('requirements', []) if item.get('scope') == 'browser']
    if not requirements:
        return None
    text = ' '.join(str(item.get('name', '')) + ' ' + str(item.get('acceptance', '')) for item in requirements)
    # This adapter deliberately handles only the complete cart/local-draft flow.
    # Search, inventory, galleries, accounts, remote mutations, etc. need their
    # own plans; never claim coverage for requirements this adapter cannot prove.
    if len(requirements) != 1 or not all(re.search(word, text, re.I) for word in (
        r'\b(cart|basket)\b', r'\bquantity\b', r'\bsubtotal\b', r'\btotal\b',
        r'\breload\b', r'\brestore\b', r'\bcancel\b', r'\bdraft\b')):
        return None
    if re.search(r'\b(filter|sort|search|gallery|variant|coupon|discount|tax|stock|inventory|account|login|upload|server|sync|remote|billing|keyboard|focus|shipping cost|delivery date)\b', text, re.I):
        return None
    source = '\n'.join((sources or {}).values())
    required_source = ("usePersistentState('cart'", 'function updateQty(', 'function placeOrder(',
                       'setCart(orderDraft.items)', 'setOrderDraft(null)', 'Restore Cart', 'Cancel Draft',
                       'aria-label="Full name"', 'aria-label="Email"', 'aria-label="Shipping address"',
                       'We do not process payments in this demo.')
    if not all(marker in source for marker in required_source):
        return None
    if re.search(r'\bfetch\s*\(|\baxios\b|\bsupabase\b|\bXMLHttpRequest\b|\bsendBeacon\b', source):
        return None
    cards = page.get_by_role('article')
    if not cards.count():
        return None
    card = cards.first
    heading = card.get_by_role('heading')
    if heading.count() != 1 or card.get_by_role('button', name='Add', exact=True).count() != 1:
        return None
    title = heading.inner_text().strip()
    if card.get_by_role('button', name='Open ' + title + ' details', exact=True).count() != 1:
        return None
    price = re.findall(r'([$€£])(\d+\.\d{2})', card.inner_text())
    cart_button = page.get_by_role('button', name=re.compile(r'^Cart with \d+ items?$'))
    if len(price) != 1 or cart_button.count() != 1:
        return None
    if cart_button.get_attribute('aria-label') != 'Cart with 0 items' or page.get_by_role('heading', name='Order draft', exact=True).count():
        # Do not remove an existing record just to fit a template's empty-cart setup.
        return None
    currency, amount = price[0]
    one, two = currency + amount, currency + format(Decimal(amount) * 2, '.2f')
    def role(kind, name, **scope):
        return dict(by='role', role=kind, name=name, **scope)
    def text_target(name, **scope):
        return dict(by='text', name=name, **scope)
    def step(action, target=None, **extra):
        return dict(action=action, **({'target': target} if target else {}), **extra)
    def click(name, **scope):
        return step('click', role('button', name, **scope))
    def visible(target):
        return step('visible', target)
    cart = {'withinRole': {'role': 'dialog', 'name': 'Cart'}}
    checkout_scope = {'withinRole': {'role': 'dialog', 'name': 'Checkout'}}
    add = click('Add', withinText=title)
    open_cart = click('Cart with', exact=False)
    quantity = {'by': 'label', 'name': 'Quantity for ' + title, **cart}
    checkout = [add, open_cart, click('Checkout', **cart)]
    draft = checkout + [
        step('fill', {'by': 'label', 'name': 'Full name'}, value='Verification Buyer'),
        step('fill', {'by': 'label', 'name': 'Email'}, value='buyer@example.test'),
        step('fill', {'by': 'label', 'name': 'Shipping address'}, value='1 Test Lane'),
        click('Place order (draft)', **checkout_scope), visible(role('heading', 'Order draft'))]
    flows = [
        ('Add from card and verify header count and cart', [add,
            visible(role('button', 'Cart with 1 items')), open_cart,
            visible(text_target(title, **cart)), visible(text_target('Total: ' + one, **cart))]),
        ('Change quantity, verify line subtotal and total, retain after reload', [add, open_cart,
            step('fill', quantity, value='2'), step('value', quantity, value='2'),
            visible(text_target(two, **cart)),
            visible({'by': 'label', 'name': 'Subtotal for ' + title, **cart}),
            step('rememberText', {'by': 'label', 'name': 'Subtotal for ' + title, **cart}, key='line'),
            visible(text_target('Total: ' + two, **cart)),
            step('reload'), open_cart, step('value', quantity, value='2'),
            step('sameText', {'by': 'label', 'name': 'Subtotal for ' + title, **cart}, key='line'),
            visible(text_target('Total: ' + two, **cart))]),
        ('Remove the synthetic item and retain empty cart after reload', [add, open_cart,
            click('Remove', withinText=title, **cart), visible(text_target('Your cart is empty.', **cart)),
            visible(role('button', 'Cart with 0 items')), step('reload'), open_cart,
            visible(text_target('Your cart is empty.', **cart))]),
        ('Reject invalid checkout without creating a draft', checkout + [
            click('Place order (draft)', **checkout_scope), visible(text_target('Full name is required.')),
            visible(text_target('A valid email is required.')), visible(text_target('Shipping address is required.')),
            step('absent', role('heading', 'Order draft'))]),
        ('Persist a local draft and restore its exact cart', draft + [step('reload'),
            visible(role('heading', 'Order draft')), click('Restore Cart'), step('absent', role('heading', 'Order draft')),
            open_cart, visible(text_target(title, **cart)), visible(text_target('Total: ' + one, **cart))]),
        ('Create a separate draft and cancel it persistently', draft + [click('Cancel Draft'), step('reload'),
            step('absent', role('heading', 'Order draft')), open_cart,
            visible(text_target('Your cart is empty.', **cart))]),
        ('Add from product details', [click('Open ' + title + ' details'),
            visible(role('heading', title, withinRole={'role': 'dialog', 'name': title})), click('Add to cart'),
            open_cart, visible(text_target(title, **cart)), visible(text_target('Total: ' + one, **cart))]),
    ]
    ids = [item['id'] for item in requirements]
    return {'requirements': requirements, 'checks': [dict(name=name, covers=ids, independent=True, steps=steps) for name, steps in flows],
            'unverified': ['Visual review and real payment processing are outside this local cart/draft adapter.'],
            'unverifiedCore': [], 'coreRequestEvidence': [], 'planner': 'observed-local-cart-v1'}
