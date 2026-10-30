from agent.functional_verification import normalize_plan_controls


def test_fill_uses_observed_accessible_label():
    step = {'action': 'fill', 'target': {'by': 'field', 'name': 'email'}, 'value': 'invalid'}
    plan = {'checks': [{'steps': [step], 'covers': ['validation']}]}
    normalize_plan_controls(plan, [{'fieldName': 'email', 'name': 'Email address', 'type': 'email'}])
    assert step['target'] == {'by': 'label', 'name': 'Email address'}
    assert plan['checks'][0]['covers'] == ['validation']


def test_ambiguous_or_hidden_field_is_not_guessed():
    for controls in ([{'fieldName': 'name', 'name': 'Name', 'type': 'hidden'}],
                     [{'fieldName': 'name', 'name': 'Name', 'type': 'text'}] * 2):
        step = {'action': 'fill', 'target': {'by': 'field', 'name': 'name'}}
        normalize_plan_controls({'checks': [{'steps': [step]}]}, controls)
        assert step['target']['by'] == 'field'


def test_close_cannot_be_skipped_by_background_content():
    step = {'action': 'click', 'target': {'by': 'role', 'name': 'Close cart'},
            'unlessVisible': {'by': 'text', 'name': 'Cart'}}
    assertion = {'action': 'absent', 'target': {'by': 'role', 'role': 'dialog', 'name': 'Cart'}}
    normalize_plan_controls({'checks': [{'steps': [step, assertion]}]}, [])
    assert 'unlessVisible' not in step
    assert assertion['action'] == 'absent'


def test_corrupted_punctuation_requires_complete_observed_line():
    spec = {'by': 'text', 'name': 'Tools \x02 $59.00', 'exact': False}
    normalize_plan_controls({'checks': [{'steps': [{'action': 'visible', 'target': spec}]}]},
                            [], 'Filters\nTools • $59.00\nOther products')
    assert spec == {'by': 'text', 'name': 'Tools • $59.00', 'exact': True}
    invalid = {'by': 'text', 'name': 'Missing \x02 $59.00'}
    normalize_plan_controls({'checks': [{'steps': [{'action': 'visible', 'target': invalid}]}]},
                            [], 'Tools • $59.00')
    assert '\x02' in invalid['name']


def test_stale_open_cart_badge_uses_unique_observed_control():
    from agent.functional_verification import observed_control_target
    class Buttons:
        def evaluate_all(self, _):
            return [{'index': 0, 'name': 'Open cart, 2 items', 'text': 'Cart (2)',
                     'visible': True, 'contexts': []}]
        def nth(self, index):
            return ('button', index)
    class Page:
        def locator(self, _):
            return Buttons()
    assert observed_control_target(Page(), {'by': 'role', 'role': 'button', 'name': 'Open cart, 0 items'}) == ('button', 0)
    assert observed_control_target(Page(), {'by': 'role', 'role': 'button', 'name': 'Remove item 0'}) is None


def test_corrupted_product_names_and_scopes_use_unique_observed_evidence():
    title = '72\u2011Hour Survival Kit (Basic)'
    steps = [
        {'action': 'visible', 'target': {'by': 'text', 'name': '72\nHour Survival Kit (Basic)'}},
        {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Open 72\tHour Survival Kit (Basic) details'}},
        {'action': 'click', 'target': {'by': 'role', 'role': 'button', 'name': 'Add', 'withinText': '72\nHour Survival Kit (Basic)'}},
    ]
    normalize_plan_controls({'checks': [{'steps': steps}]},
                            [{'name': 'Open ' + title + ' details'}], title)
    assert steps[0]['target']['name'] == title
    assert steps[1]['target']['name'] == 'Open ' + title + ' details'
    assert steps[2]['target']['withinText'] == title


def test_corruption_repair_does_not_guess_between_distinct_products():
    spec = {'by': 'text', 'name': '72\nHour Kit'}
    normalize_plan_controls({'checks': [{'steps': [{'action': 'visible', 'target': spec}]}]},
                            [], '72-Hour Kit\n72\u2011Hour Kit')
    assert spec['name'] == '72\nHour Kit'
