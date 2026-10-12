from agent.progress import execution_timeout


def test_background_review_has_separate_bounded_deadline(monkeypatch):
    monkeypatch.delenv('GENESYS_BACKGROUND_TIMEOUT_SECONDS', raising=False)
    assert execution_timeout(240, background=True) == 600
    assert execution_timeout(900, background=False) == 240
    assert execution_timeout(60, background=False) == 60
    monkeypatch.setenv('GENESYS_BACKGROUND_TIMEOUT_SECONDS', '5000')
    assert execution_timeout(240, background=True) == 900
