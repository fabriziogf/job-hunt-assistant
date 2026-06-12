"""Tests for the LLM X/Y/Z rewriter.

These use a fake Anthropic client, so they run without an API key or network.
They verify the grounding/prompt logic and the honesty gate — not model quality.
"""

import pytest

from job_hunt_assistant.profile import Achievement
from job_hunt_assistant.resume import (
    BulletRewrite,
    ResumeRewriter,
    build_rewrite_prompt,
)


# --- Fakes -------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, parsed: BulletRewrite) -> None:
        self.parsed_output = parsed


class _FakeMessages:
    def __init__(self, parsed: BulletRewrite) -> None:
        self._parsed = parsed
        self.calls: list[dict] = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._parsed)


class _FakeClient:
    def __init__(self, parsed: BulletRewrite) -> None:
        self.messages = _FakeMessages(parsed)


# --- Prompt construction (pure) ----------------------------------------------


def test_prompt_includes_xyz_formula_and_honesty_rules():
    a = Achievement(
        what="Launched a recommender",
        measured_by="3% lift",
        how="staged A/B rollouts",
        verified=True,
    )
    system, user = build_rewrite_prompt(a)
    assert "[X]" in system and "[Y]" in system and "[Z]" in system  # playbook formula
    assert "NEVER invent" in system  # honesty rules present
    assert "Launched a recommender" in user
    assert "3% lift" in user


def test_prompt_flags_missing_metric_without_inventing():
    a = Achievement(what="Established governance framework", verified=True)
    _, user = build_rewrite_prompt(a)
    assert "do not invent one" in user.lower()


def test_prompt_includes_job_description_when_given():
    a = Achievement(what="Built data pipelines", verified=True)
    _, user = build_rewrite_prompt(a, job_description="Seeking stakeholder management")
    assert "stakeholder management" in user


# --- Rewriter behavior -------------------------------------------------------


def test_rewrite_calls_model_with_schema_and_returns_parsed():
    expected = BulletRewrite(rewritten="Launched X, lifting Y by 3%.", has_metric=True)
    client = _FakeClient(expected)
    rewriter = ResumeRewriter(client=client)

    result = rewriter.rewrite(
        Achievement(what="Launched X", measured_by="3%", verified=True)
    )

    assert result is expected
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert call["output_format"] is BulletRewrite  # structured output enforced
    assert call["system"] and call["messages"]


def test_rewrite_refuses_unverified_achievement():
    rewriter = ResumeRewriter(client=_FakeClient(BulletRewrite(rewritten="x", has_metric=False)))
    with pytest.raises(ValueError, match="unverified"):
        rewriter.rewrite(Achievement(what="Unconfirmed claim", verified=False))


def test_rewrite_verified_skips_unverified_in_batch():
    client = _FakeClient(BulletRewrite(rewritten="ok", has_metric=True))
    rewriter = ResumeRewriter(client=client)
    achievements = [
        Achievement(what="Real A", measured_by="10%", verified=True),
        Achievement(what="Unverified B", verified=False),
        Achievement(what="Real C", measured_by="20%", verified=True),
    ]
    results = rewriter.rewrite_verified(achievements)
    assert len(results) == 2  # only the two verified ones were rewritten
    assert len(client.messages.calls) == 2
