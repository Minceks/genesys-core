import pytest

from agent.promotion import (
    PROMOTION_PROOF_TTL_SECONDS,
    sign_verified_checkpoint,
    verify_checkpoint_promotion_token,
)

KEY = "test-only-signing-key-not-for-production"
PROJECT = "test-project"
CHECKPOINT = "genesys-checkpoint-123"
COMMIT = "a" * 40


def make_token():
    return sign_verified_checkpoint(
        signing_key=KEY,
        project_id=PROJECT,
        checkpoint_id=CHECKPOINT,
        checkpoint_commit=COMMIT,
    )


def verify(token, *, project=PROJECT, checkpoint=CHECKPOINT):
    return verify_checkpoint_promotion_token(
        token,
        signing_key=KEY,
        project_id=project,
        checkpoint_id=checkpoint,
    )


def test_valid_token_returns_signed_commit():
    assert verify(make_token()) == COMMIT


def test_modified_signature_is_rejected():
    token = make_token()
    encoded, signature = token.split(".", 1)
    replacement = "A" if signature[0] != "A" else "B"
    assert verify(f"{encoded}.{replacement}{signature[1:]}") is None


def test_wrong_project_is_rejected():
    assert verify(make_token(), project="another-project") is None


def test_wrong_checkpoint_is_rejected():
    assert verify(make_token(), checkpoint="genesys-checkpoint-999") is None


def test_expired_token_is_rejected(monkeypatch):
    import agent.promotion as promotion

    monkeypatch.setattr(promotion.time, "time", lambda: 1_000_000)
    token = make_token()
    monkeypatch.setattr(
        promotion.time,
        "time",
        lambda: 1_000_000 + PROMOTION_PROOF_TTL_SECONDS + 1,
    )
    assert verify(token) is None


@pytest.mark.parametrize("token", ["", "not-a-token", "a.b.c", "!.!!!!"])
def test_malformed_token_is_rejected(token):
    assert verify(token) is None
