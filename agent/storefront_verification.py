"""Bounded browser recipes for the local catalog/cart/pending-order starter.

Only the explicitly supported acceptance contract and source shape are eligible.
Unknown requirements go to the general planner. Every outcome is checked live.
"""
import re
from decimal import Decimal

SUPPORTED = {'Browse product catalog': 'Open Shop, verify product names, images and prices, and open a product '
                           'detail view.',
 'View product details': 'Open a product detail and verify its name, image, price and description; '
                         'choose quantity and add that quantity to the cart. Reload retains the '
                         'selected product view.',
 'Add item to cart and persist locally': 'Add a product to the cart, reload and reopen the cart if '
                                         'necessary; verify the saved item and quantity. A new '
                                         'same-origin tab can read the saved cart.',
 'Update cart quantities and remove items': 'Increase and decrease cart quantities, verify line '
                                            'total and subtotal, reload and reopen the cart to '
                                            'verify the saved quantity, then remove the item and '
                                            'verify removal after reload.',
 'Checkout submission with validation': 'Submit an empty checkout and verify inline errors; '
                                        'invalid email is rejected. Submit valid contact and '
                                        'shipping details to create a pending local order, clear '
                                        'the cart and show confirmation. Reload retains the '
                                        'confirmation for this session. No real payment processing '
                                        'is included.'}


def storefront_plan(page, contract, sources):
    requirements = [r for r in (contract or {}).get('requirements', []) if r.get('scope') == 'browser']
    if len(requirements) != len(SUPPORTED) or {r.get('name') for r in requirements} != set(SUPPORTED):
        return None
    if any(r.get('acceptance') != SUPPORTED[r['name']] for r in requirements):
        return None
    source = '\n'.join((sources or {}).values())
    markers = ("usePersistentState('cart'", "usePersistentState('view'", 'const PRODUCTS = [',
               'function addToCart(', 'function updateQuantity(', 'function removeItem(',
               'Submit order (no payment)', "sessionStorage.setItem('lastOrder'", '<form noValidate',
               'aria-label={`Quantity for ${p.name}`}', 'aria-label={`Increase quantity for ${item.name}`}')
    if not all(marker in source for marker in markers) or re.search(r'\bfetch\s*\(|\b(?:axios|supabase|XMLHttpRequest|sendBeacon)\b', source):
        return None
    product = re.search(r"name:\s*'([^'\n]+)'[\s,]+price:\s*(\d+(?:\.\d+)?)", source)
    if not product or page.get_by_role('button', name='Shop', exact=True).count() != 1:
        return None
    title, amount = product.groups()
    description = re.search(r"description:\s*\[\s*'([^'\n]+)'", source)
    image = re.search(r'role="img" aria-label="([^"]+)"', source)
    if not description or not image:
        return None
    price = Decimal(amount)
    ids = {r['name']:r['id'] for r in requirements}
    def role(kind, name, **extra): return dict(by='role', role=kind, name=name, exact=True, **extra)
    def text(name, **extra): return dict(by='text', name=name, exact=True, **extra)
    def step(action, target=None, **extra): return dict(action=action, **({'target':target} if target else {}), **extra)
    def click(name, **extra): return step('click', role('button', name, **extra))
    def visible(target): return step('visible', target)
    quantity = dict(by='label', name='Quantity for '+title, exact=True)
    shop = click('Shop')
    details = [shop, step('click', text('View', withinText=title))]
    add = [shop, step('click', dict(by='text', name='Add to cart', exact=False, withinText=title))]
    cart = step('click', dict(by='role', role='button', name='Open cart with', exact=False))
    checkout = add + [cart, click('Proceed to checkout')]
    fields = [step('type' if n == 'Name' else 'fill', dict(by='label', name=n, exact=True), value=v) for n,v in (
        ('Name','Verification Buyer'), ('Email','buyer@example.test'), ('Shipping address','1 Test Lane'))]
    flows = [
      ('Browse product catalog', 'Catalog names, image, price and real detail navigation', [shop, visible(role('heading',title)), visible(role('img',image.group(1))),
         step('click',text('View',withinText=title)), visible(role('heading', title)), visible(text('$'+format(price,'.2f'))),
         visible(role('button','Add to cart'))]),
      ('View product details', 'Detail description and selected product survive reload', details + [
         visible(role('heading',title)), visible(text(description.group(1))),
         step('reload'), visible(role('heading',title)), visible(role('button','Add to cart'))]),
      ('View product details', 'Selected quantity controls the number of items added', details + [
         step('fill', quantity, value='2'), click('Add to cart'), step('value',quantity,value='2'),
         visible(text('$'+format(price*2,'.2f')))]),
      ('Add item to cart and persist locally', 'Cart item and quantity persist after reload and in a real new tab', add + [cart,
         step('value',quantity,value='1'), step('reload'), cart, visible(text(title)),
         step('value',quantity,value='1'), step('newTabValue',quantity,value='1')]),
      ('Update cart quantities and remove items', 'Quantity, line total, subtotal, reload and persistent removal', add + [cart,
         click('Increase quantity for '+title), step('value',quantity,value='2'),
         visible(text('$'+format(price*2,'.2f'),withinText=title)),
         visible(text('$'+format(price*2,'.2f'),withinRole={'role':'complementary','name':''})), step('reload'), cart, step('value',quantity,value='2'),
         click('Decrease quantity for '+title), step('value',quantity,value='1'),
         click('Remove',withinText=title), step('reload'), cart, step('absent',text(title))]),
      ('Checkout submission with validation', 'Required and email validation, pending local order, confirmation and cart clearing', checkout + [
         click('Submit order (no payment)'), visible(role('alert','')), *fields,
         step('fill',dict(by='label',name='Email',exact=True),value='invalid'), click('Submit order (no payment)'),
         visible(role('alert','')), step('fill',dict(by='label',name='Email',exact=True),value='buyer@example.test'),
         click('Submit order (no payment)'), visible(role('heading','Order submitted')), step('reload'),
         visible(role('heading','Order submitted')), visible(text('Verification Buyer')), cart, step('absent',text(title))]),
    ]
    return {'checks':[dict(name=name,covers=[ids[key]],independent=True,steps=steps) for key,name,steps in flows],
            'requirements':requirements,'unverified':['Visual review and real payment processing are separate from these local browser checks.'],
            'unverifiedCore':[],'coreRequestEvidence':[],'planner':'observed-local-storefront-v1'}
