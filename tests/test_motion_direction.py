from agent.design_execution import design_execution
from agent.motion_direction import motion_direction


def test_cinematic_request_receives_motion_handoff_without_changing_theme():
    brief = {'originalRequest': 'Build a cinematic camera launch',
             'designStrategy': {'direction': 'Ivory editorial'}}
    handoff = design_execution(brief)
    assert handoff['artAndMotion']['mode'] == 'cinematic-candidate'
    assert handoff['direction'] == 'Ivory editorial'
    assert 'originalRequest' in brief and 'artAndMotion' not in brief


def test_regular_apps_and_later_repairs_do_not_trigger_cinematic_scope():
    handoff = motion_direction({'originalRequest': 'An accounting dashboard',
                                'latestRequest': 'Fix the cinematic video link'})
    assert handoff['mode'] == 'purposeful-interface'
    assert 'Preserve existing scope on repairs' in handoff['selection']


def test_motion_contract_requires_bounded_loading_and_honest_fallback_evidence():
    policy = motion_direction({'originalRequest': 'An image-sequence product story'})
    rules = ' '.join(policy['motionContract'])
    assert 'bounded neighboring-frame window' in rules
    assert 'Do not replace reduced motion with a looping video' in rules
    assert 'retry or skip control' in rules
    assert 'keyboard-accessible' in rules
    assert 'forward and reverse' in ' '.join(policy['evidence'])
    assert 'remaining budget' in ' '.join(policy['assetContract'])


def test_policies_are_independent_between_projects():
    first = motion_direction({})
    first['motionContract'].clear()
    assert motion_direction({})['motionContract']
