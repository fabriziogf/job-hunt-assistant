"""Interview question bank + the practice math (Chapter 6).

Chapter 6's insight: interviews are nearly identical, so you can predict the
questions and prepare. It gives 12 near-certain questions and says to brainstorm
~30 total, then do the arithmetic: 30 questions x 2 answers x 3 reps = 180 reps
~= 13.5 hours.

This module holds the canonical 12 as structured data, a ``QuestionBank`` to
collect ~30, and ``practice_plan()`` which turns a question count into the rep
count and hour estimate.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class QuestionCategory(str, Enum):
    MOTIVATIONAL = "motivational"  # why this role / company
    BEHAVIORAL = "behavioral"  # tell me about a time...
    SELF_ASSESSMENT = "self_assessment"  # strengths / weaknesses
    LOGISTICS = "logistics"  # leaving, salary, timeline
    CLOSING = "closing"  # your questions for us
    ROLE_SPECIFIC = "role_specific"  # tailored to the job (LLM-generated)


class InterviewQuestion(BaseModel):
    text: str
    category: QuestionCategory
    canonical: bool = False  # one of the 12 near-certain questions


# The 12 questions Chapter 6 says you'll almost certainly be asked.
CANONICAL_QUESTIONS: list[InterviewQuestion] = [
    InterviewQuestion(text="Tell me about yourself.", category=QuestionCategory.MOTIVATIONAL, canonical=True),
    InterviewQuestion(text="Why this role?", category=QuestionCategory.MOTIVATIONAL, canonical=True),
    InterviewQuestion(text="Why this company?", category=QuestionCategory.MOTIVATIONAL, canonical=True),
    InterviewQuestion(text="What's your greatest strength?", category=QuestionCategory.SELF_ASSESSMENT, canonical=True),
    InterviewQuestion(text="What's your greatest weakness?", category=QuestionCategory.SELF_ASSESSMENT, canonical=True),
    InterviewQuestion(text="Tell me about a time you led a team.", category=QuestionCategory.BEHAVIORAL, canonical=True),
    InterviewQuestion(text="Tell me about a time you failed.", category=QuestionCategory.BEHAVIORAL, canonical=True),
    InterviewQuestion(text="Tell me about a difficult coworker.", category=QuestionCategory.BEHAVIORAL, canonical=True),
    InterviewQuestion(text="Why are you leaving your current job?", category=QuestionCategory.LOGISTICS, canonical=True),
    InterviewQuestion(text="Where do you see yourself in 5 years?", category=QuestionCategory.LOGISTICS, canonical=True),
    InterviewQuestion(text="What are your salary expectations?", category=QuestionCategory.LOGISTICS, canonical=True),
    InterviewQuestion(text="Do you have any questions for us?", category=QuestionCategory.CLOSING, canonical=True),
]

# Chapter 6 target: brainstorm about this many questions total.
TARGET_QUESTION_COUNT = 30


def canonical_questions() -> list[InterviewQuestion]:
    """A fresh copy of the 12 near-certain questions."""
    return [q.model_copy() for q in CANONICAL_QUESTIONS]


class QuestionBank(BaseModel):
    """A collection of likely interview questions (aim for ~30)."""

    questions: list[InterviewQuestion] = Field(default_factory=list)

    @classmethod
    def with_canonical(cls) -> "QuestionBank":
        return cls(questions=canonical_questions())

    def add(self, question: InterviewQuestion) -> None:
        self.questions.append(question)

    def by_category(self, category: QuestionCategory) -> list[InterviewQuestion]:
        return [q for q in self.questions if q.category is category]

    @property
    def count(self) -> int:
        return len(self.questions)

    @property
    def meets_target(self) -> bool:
        return self.count >= TARGET_QUESTION_COUNT


# --- The practice math -------------------------------------------------------

# 180 reps ≈ 13.5 hours -> 4.5 minutes per spoken-aloud rep.
MINUTES_PER_REP = 4.5
DEFAULT_ANSWERS_EACH = 2
DEFAULT_REPS_EACH = 3


class PracticePlan(BaseModel):
    """How much practice a question bank implies (Chapter 6's arithmetic)."""

    questions: int
    answers_each: int = DEFAULT_ANSWERS_EACH
    reps_each: int = DEFAULT_REPS_EACH

    @property
    def total_reps(self) -> int:
        return self.questions * self.answers_each * self.reps_each

    @property
    def estimated_hours(self) -> float:
        return round(self.total_reps * MINUTES_PER_REP / 60, 1)

    def summary(self) -> str:
        return (
            f"{self.questions} questions x {self.answers_each} answers x "
            f"{self.reps_each} reps = {self.total_reps} reps "
            f"(~{self.estimated_hours} hours), spread over a week of evenings."
        )


def practice_plan(
    num_questions: int,
    answers_each: int = DEFAULT_ANSWERS_EACH,
    reps_each: int = DEFAULT_REPS_EACH,
) -> PracticePlan:
    """Turn a question count into a rep count and hour estimate."""
    return PracticePlan(
        questions=num_questions, answers_each=answers_each, reps_each=reps_each
    )
