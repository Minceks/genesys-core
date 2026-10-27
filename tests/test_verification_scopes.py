from agent.build_spec import verification_scopes


def test_actual_external_handoff_is_reported_separately_without_removing_it():
    spec = {'requirements': [
        {'id': 'payment', 'scope': 'browser', 'acceptance': 'visitor is redirected to a documented external payment URL'},
        {'id': 'validation', 'scope': 'browser', 'acceptance': 'form blocks invalid input and shows external redirect failures'},
        {'id': 'persistence', 'scope': 'browser', 'acceptance': 'cart persists until explicit clear or successful external payment redirect'}]}
    normalized = verification_scopes(spec)
    assert normalized['requirements'][0]['scope'] == 'external'
    assert normalized['requirements'][1]['scope'] == 'browser'
    assert normalized['requirements'][2]['scope'] == 'browser'
    assert spec['requirements'][0]['scope'] == 'browser'
    assert len(normalized['requirements']) == 3
