"""Constrained output for the browser verification planner."""


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


TEXT = {'type': 'string', 'pattern': r'^[^\x00-\x08\x0b\x0c\x0e-\x1f]*$'}
READ_ONLY_ATTRIBUTES = ['aria-pressed', 'aria-selected', 'aria-expanded', 'src', 'href', 'min', 'max', 'type', 'required', 'disabled', 'viewBox']
NONEMPTY = dict(TEXT, minLength=1)
STRINGS = {'type': 'array', 'items': NONEMPTY}
SCOPE = obj({'role': {'type': 'string', 'enum': ['navigation', 'banner', 'region', 'form', 'dialog', 'alertdialog', 'complementary']}, 'name': TEXT})
TARGET_FIELDS = {'name': TEXT, 'exact': {'type': 'boolean'},
                 'withinText': {'type': ['string', 'null']}, 'withinRole': {'anyOf': [SCOPE, {'type': 'null'}]}}
TARGET = {'anyOf': [obj({'by': {'type': 'string', 'enum': ['role']},
    'role': {'type': 'string', 'enum': ['button', 'link', 'heading', 'img', 'dialog', 'alertdialog',
        'alert', 'status', 'navigation', 'banner', 'region', 'form', 'article', 'group', 'list',
        'listitem', 'row', 'textbox', 'spinbutton', 'combobox', 'checkbox', 'radio', 'option']},
    **TARGET_FIELDS, 'name': NONEMPTY}), obj({'by': {'type': 'string', 'enum': ['label', 'text', 'placeholder', 'field']}, **TARGET_FIELDS, 'name': NONEMPTY})]}


def unnamed_roles(roles):
    return obj({'by': {'type': 'string', 'enum': ['role']},
                'role': {'type': 'string', 'enum': roles}, **TARGET_FIELDS,
                'name': {'type': 'string', 'enum': ['']}})


VISIBILITY_TARGET = {'anyOf': [*TARGET['anyOf'], unnamed_roles(['alert', 'status', 'dialog', 'alertdialog'])]}
DESTINATION_TARGET = {'anyOf': [*TARGET['anyOf'], unnamed_roles(['dialog', 'alertdialog'])]}


def step(actions, target=TARGET, **properties):
    return obj({'action': {'type': 'string', 'enum': actions}, 'target': target, **properties})


ASSERTION = {'anyOf': [step(['visible', 'absent'], target=VISIBILITY_TARGET), step(['invalid', 'focused']), step(['value', 'newTabValue', 'newTabText'], value=TEXT),
                       step(['sameText'], key=NONEMPTY), step(['attribute'],
                       attribute={'type': 'string', 'enum': READ_ONLY_ATTRIBUTES}, value=TEXT)]}
STEP = {'anyOf': [*ASSERTION['anyOf'], step(['fill', 'type', 'select'], value=TEXT),
                   step(['click'], unlessVisible={'anyOf': [DESTINATION_TARGET, {'type': 'null'}]}),
                   step(['rememberText'], key=NONEMPTY), obj({'action': {'type': 'string', 'enum': ['reload', 'tab']}})]}
PLAN_SCHEMA = obj({
    'checks': {'type': 'array', 'minItems': 1, 'maxItems': 8, 'items': obj({
        'name': NONEMPTY, 'covers': dict(STRINGS, minItems=1), 'independent': {'type': 'boolean'},
        'steps': {'type': 'array', 'maxItems': 23, 'items': STEP}, 'finalAssertion': ASSERTION})},
    'requirements': {'type': 'array', 'minItems': 1, 'items': obj({'id': NONEMPTY, 'name': NONEMPTY})},
    'unverified': STRINGS, 'unverifiedCore': STRINGS,
    'coreRequestEvidence': {'type': 'array', 'items': obj({'requirement': NONEMPTY, 'requestQuote': NONEMPTY})},
})


def executable_plan(plan):
    def clean(value):
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items() if item is not None}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value
    plan = clean(plan)
    for check in plan.get('checks', []):
        if 'finalAssertion' in check:
            check['steps'].append(check.pop('finalAssertion'))
    return plan


def complete_text_captures(plan):
    """Fill a missing capture only at an existing matching prior observation.

    Captures still run in the browser and require a unique visible nonempty
    element. Never invent a locator, key, expected value or cross-check state.
    """
    from copy import deepcopy
    plan = deepcopy(plan)
    captured = set()
    for check in plan.get('checks', []):
        if not isinstance(check, dict) or not isinstance(check.get('steps'), list):
            continue
        steps = check['steps']
        if check.get('independent') is True:
            captured = set()
        inserts = {}
        for index, item in enumerate(steps):
            if not isinstance(item, dict):
                continue
            key = item.get('key')
            if not isinstance(key, str) or not key.strip():
                continue
            if item.get('action') == 'rememberText':
                captured.add(key)
            if item.get('action') != 'sameText' or key in captured:
                continue
            target = item.get('target')
            if not isinstance(target, dict) or not isinstance(target.get('name'), str) or not target['name'].strip():
                continue
            previous = next((i for i, candidate in enumerate(steps[:index])
                             if isinstance(candidate, dict) and candidate.get('action') == 'visible'
                             and candidate.get('target') == target), None)
            if previous is not None:
                inserts.setdefault(previous, []).append({'action': 'rememberText', 'target': deepcopy(target), 'key': key})
                captured.add(key)
        check['steps'] = [part for i, item in enumerate(steps) for part in [item, *inserts.get(i, [])]]
    return plan
