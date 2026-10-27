from agent import promotion


def test_stale_checkpoint_is_rejected_without_github_writes(monkeypatch):
    calls = []

    def fake_github_request(url, **kwargs):
        calls.append((url, kwargs))
        if "/pulls?" in url:
            return {"status": "success", "data": []}
        if "/git/ref/heads/" in url:
            return {"status": "success", "data": {"object": {"sha": "b" * 40}}}
        raise AssertionError(f"Unexpected GitHub API request: {url}")

    monkeypatch.setattr(promotion, "_github_request", fake_github_request)
    result = promotion.create_verified_pull_request(
        token="test-only-token",
        repository="example/project",
        base="main",
        checkpoint_id="genesys-checkpoint-123",
        parent_commit="a" * 40,
        project_key="test-project",
        changes=[{
            "path": "README.md",
            "status": "M",
            "mode": "100644",
            "contentBase64": "dGVzdA==",
        }],
    )
    assert result["status"] == "error"
    assert result["code"] == "STALE_CHECKPOINT"
    assert len(calls) == 2


def test_existing_pr_does_not_bypass_stale_checkpoint_check(monkeypatch):
    calls = []

    def fake_github_request(url, **kwargs):
        calls.append(url)
        if "/pulls?" in url:
            return {
                "status": "success",
                "data": [{"number": 42, "html_url": "https://example.invalid/pr/42"}],
            }
        if "/git/ref/heads/" in url:
            return {
                "status": "success",
                "data": {"object": {"sha": "b" * 40}},
            }
        raise AssertionError(f"Unexpected GitHub API request: {url}")

    monkeypatch.setattr(promotion, "_github_request", fake_github_request)

    result = promotion.create_verified_pull_request(
        token="test-only-token",
        repository="example/project",
        base="main",
        checkpoint_id="genesys-checkpoint-123",
        parent_commit="a" * 40,
        project_key="test-project",
        changes=[{
            "path": "README.md",
            "status": "M",
            "mode": "100644",
            "contentBase64": "dGVzdA==",
        }],
    )

    assert result["status"] == "error"
    assert result["code"] == "STALE_CHECKPOINT"
    assert len(calls) == 2