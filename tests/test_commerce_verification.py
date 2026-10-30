from agent.commerce_verification import commerce_plan


def contract(acceptance):
    return {'requirements': [{'id': 'R1', 'scope': 'browser', 'name': 'Cart flow', 'acceptance': acceptance}]}


def test_unknown_features_never_receive_template_coverage():
    core = 'cart quantity subtotal total reload restore cancel draft'
    for extra in ('stock', 'filter', 'server', 'gallery', 'account', 'tax'):
        assert commerce_plan(None, contract(core + ' ' + extra), {}) is None


def test_template_requires_complete_contract_and_proven_source_shape():
    assert commerce_plan(None, contract('Add a cart item'), {}) is None
    assert commerce_plan(None, contract('cart quantity subtotal total reload restore cancel draft'), {}) is None
    assert commerce_plan(None, None, {}) is None
