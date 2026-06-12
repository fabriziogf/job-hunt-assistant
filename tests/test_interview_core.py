"""Tests for the deterministic interview-prep core (no API key)."""

from datetime import date

import pytest

from job_hunt_assistant.interview import (
    Answer,
    AnsweredQuestion,
    InterviewLog,
    QuestionBank,
    QuestionCategory,
    canonical_questions,
    closing_questions,
    coaching_points,
    instant_rejections,
    lint_answer,
    practice_plan,
)


# --- Questions + practice math ----------------------------------------------


def test_canonical_has_twelve_questions():
    qs = canonical_questions()
    assert len(qs) == 12
    assert all(q.canonical for q in qs)
    assert qs[0].text == "Tell me about yourself."


def test_question_bank_target_and_categories():
    bank = QuestionBank.with_canonical()
    assert bank.count == 12
    assert not bank.meets_target  # need ~30
    assert len(bank.by_category(QuestionCategory.BEHAVIORAL)) == 3


def test_practice_math_matches_playbook():
    # 30 questions x 2 answers x 3 reps = 180 reps ~= 13.5 hours.
    plan = practice_plan(30)
    assert plan.total_reps == 180
    assert plan.estimated_hours == 13.5


# --- Answer structure linter ------------------------------------------------


def _complete_answer() -> Answer:
    return Answer(
        restate="You're asking about a time I led a team.",
        preview="I'll describe leading a 40-person launch.",
        story="I led a cross-functional team of 40 to launch a recommender that "
        "lifted acquisition by 3% and added $40M in revenue over the year.",
        summary="So I lead by aligning a large team around a measurable goal.",
        achievement_tag="recommender-launch",
    )


def test_complete_answer_passes():
    report = lint_answer(_complete_answer())
    assert not report.warnings  # all four parts present


def test_missing_parts_flagged():
    answer = _complete_answer()
    answer.preview = ""
    answer.summary = ""
    report = lint_answer(answer)
    assert report.by_code("missing_preview")
    assert report.by_code("missing_summary")


def test_story_without_numbers_flagged_as_info():
    answer = _complete_answer()
    answer.story = "I led a team and we did really well and everyone was happy."
    report = lint_answer(answer)
    assert report.by_code("story_not_quantified")


# --- Post-interview log ------------------------------------------------------


def test_log_average_weakest_and_followups():
    log = InterviewLog(
        company="Northwind",
        role="PM",
        interview_date=date(2026, 6, 11),
        answered=[
            AnsweredQuestion(question="Tell me about yourself.", score=9),
            AnsweredQuestion(question="Greatest weakness?", score=4),
            AnsweredQuestion(question="Why this company?", score=6),
        ],
        new_questions=["How would you prioritize our roadmap?"],
    )
    assert log.average_score == pytest.approx(6.3, abs=0.1)
    weakest = log.weakest(1)
    assert weakest[0].question == "Greatest weakness?"
    # Scores <= 6 are flagged for rewrite (the 4 and the 6).
    assert len(log.answers_to_rewrite()) == 2
    assert log.questions_to_add() == ["How would you prioritize our roadmap?"]


def test_log_rejects_out_of_range_score():
    with pytest.raises(ValueError):
        AnsweredQuestion(question="x", score=11)


# --- Coaching (Ch. 5) --------------------------------------------------------


def test_coaching_surfaces_chapter_5_essentials():
    points = coaching_points()
    titles = " ".join(p.title.lower() for p in points)
    assert "interviewer" in titles  # "everyone you meet is your interviewer"
    assert "thank-you" in titles

    assert len(closing_questions()) == 3
    assert any("6-month" in q for q in closing_questions())

    rejections = instant_rejections()
    assert any("late" in r.lower() for r in rejections)
    assert any("salary" in r.lower() for r in rejections)
