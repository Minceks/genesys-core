from agent.storefront_verification import SUPPORTED, storefront_plan


def contract():
    return {'requirements':[dict(id=f'R{i}',name=name,scope='browser',acceptance=acceptance) for i,(name,acceptance) in enumerate(SUPPORTED.items(),1)]}


def test_storefront_unknown_acceptance_falls_back_before_browser_actions():
    spec=contract()
    spec['requirements'][0]['acceptance'] += ' Filter by stock and synchronize with a server.'
    assert storefront_plan(None,spec,{}) is None


def test_storefront_extra_requirement_is_not_silently_covered():
    spec=contract()
    spec['requirements'].append(dict(id='extra',name='Inventory',scope='browser',acceptance='Save stock to the server'))
    assert storefront_plan(None,spec,{}) is None


def test_storefront_requires_source_evidence():
    assert storefront_plan(None,contract(),{}) is None
    assert storefront_plan(None,None,{}) is None


def test_recognized_recipe_covers_each_requirement_and_uses_real_new_tab():
    class Page:
        def get_by_role(self,*args,**kwargs): return self
        def count(self): return 1
    source = """usePersistentState('cart' usePersistentState('view' const PRODUCTS = [
        {name: 'Fixture Kit', price: 10.0, description: ['Fixture description']}
        function addToCart( function updateQuantity( function removeItem(
        Submit order (no payment) sessionStorage.setItem('lastOrder' <form noValidate
        aria-label={`Quantity for ${p.name}`} aria-label={`Increase quantity for ${item.name}`}
        role="img" aria-label="Fixture product image"
    """
    spec=contract()
    plan=storefront_plan(Page(),spec,{'src/App.jsx':source})
    assert plan is not None
    assert {key for check in plan['checks'] for key in check['covers']} == {r['id'] for r in spec['requirements']}
    assert all(check['independent'] for check in plan['checks'])
    assert sum(len(check['steps']) for check in plan['checks']) <= 96
    steps=[step for check in plan['checks'] for step in check['steps']]
    catalog_actions=[step['target'] for step in steps if step['action']=='click' and step.get('target',{}).get('withinText')=='Fixture Kit']
    assert any(t['by']=='text' and t['name']=='View' and t['exact'] for t in catalog_actions)
    assert any(t['by']=='text' and t['name']=='Add to cart' for t in catalog_actions)
    assert any(step['action']=='newTabValue' and step['target']['name']=='Quantity for Fixture Kit' for step in steps)
    assert any(step.get('target',{}).get('withinRole',{}).get('role')=='complementary' for step in steps)
    assert storefront_plan(Page(),spec,{'src/App.jsx':source+" fetch('/orders')"}) is None
