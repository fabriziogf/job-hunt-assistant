"""Tests for the interview LLM generators (fake client — no API key)."""

from datetime import date

from job_hunt_assistant import load_sample_profile
from job_hunt_assistant.interview import (
    Answer,
    AnswerSet,
    QuestionCategory,
    build_answer_prompt,
    build_question_prompt,
)
from job_hunt_assistant.interview.answers import AnswerSet as AnswerSetModel
from job_hunt_assistant.interview.generator import (
    AnswerCoach,
    GeneratedQuestions,
    QuestionGenerator,
)
from job_hunt_assistant.interview.questions import InterviewQuestion
from job_hunt_assistant.profile import (
    Achievement,
    CandidateProfile,
    Contact,
    Experience,
)


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed_output = parsed


class _FakeMessages:
    def __init__(self, parsed):
        self._parsed = parsed
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._parsed)


class _FakeClient:
    def __init__(self, parsed):
        self.messages = _FakeMessages(parsed)


# --- Question generation -----------------------------------------------------


def test_question_prompt_grounds_in_interview_chapters():
    system, user = build_question_prompt(
        role="Product Manager", company="Northwind", needed=18
    )
    assert "Chapter 5" in system or "Chapter 6" in system
    assert "Northwind" in user
    assert "18 additional" in user


def test_generate_appends_to_canonical_and_hits_target():
    extra = GeneratedQuestions(
        questions=[
            InterviewQuestion(
                text=f"Role-specific Q{i}", category=QuestionCategory.ROLE_SPECIFIC
            )
            for i in range(18)
        ]
    )
    gen = QuestionGenerator(client=_FakeClient(extra))
    bank = gen.generate(role="PM", company="Northwind", target=30)
    assert bank.count == 30
    assert bank.meets_target
    # Asked the model for exactly the shortfall (30 - 12).
    assert "18 additional" in gen._client.messages.calls[0]["messages"][0]["content"]


def test_generate_skips_model_when_target_already_met():
    gen = QuestionGenerator(client=_FakeClient(GeneratedQuestions()))
    bank = gen.generate(role="PM", company="Northwind", target=10)
    assert bank.count == 12  # canonical already exceeds a target of 10
    assert gen._client.messages.calls == []  # no model call


# --- Answer coaching ---------------------------------------------------------


def test_answer_prompt_uses_only_verified_achievements():
    profile = CandidateProfile(
        contact=Contact(full_name="Test", email="t@example.com"),
        experiences=[
            Experience(
                company="Acme",
                title="PM",
                start=date(2023, 1, 1),
                achievements=[
                    Achievement(what="Real verified win", measured_by="20%", verified=True),
                    Achievement(what="Unverified secret", verified=False),
                ],
            )
        ],
    )
    system, user = build_answer_prompt("Tell me about a time you led a team.", profile)
    assert "four-part structure" in system
    assert "Real verified win" in user
    assert "Unverified secret" not in user


def test_answer_coach_calls_model_and_records_question():
    drafted = AnswerSetModel(
        question="(placeholder)",
        answers=[
            Answer(restate="r1", preview="p1", story="s1 with 3 metrics", summary="m1"),
            Answer(restate="r2", preview="p2", story="s2 with 5 metrics", summary="m2"),
        ],
    )
    coach = AnswerCoach(client=_FakeClient(drafted))
    result = coach.generate("Tell me about a time you failed.", load_sample_profile())
    assert isinstance(result, AnswerSet)
    assert result.question == "Tell me about a time you failed."  # recorded
    assert len(result.answers) == 2
    call = coach._client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert call["output_format"] is AnswerSetModel
