"""Post-interview log + self-scoring (Chapter 6: "keep the list alive").

Within 30 minutes of every interview: write down every question you got, score
yourself out of 10, add the questions you didn't predict, and rewrite your
weakest answers. This module models that log and surfaces what to act on — the
lowest-scoring answers and the new questions to fold into your bank.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

MAX_SCORE = 10
# Score at or below this is a "weak" answer worth rewriting before bed.
WEAK_SCORE_THRESHOLD = 6


class AnsweredQuestion(BaseModel):
    """A question you were asked, with an honest self-score out of 10."""

    question: str
    score: int  # 0-10
    notes: str | None = None

    @field_validator("score")
    @classmethod
    def _in_range(cls, v: int) -> int:
        if not 0 <= v <= MAX_SCORE:
            raise ValueError(f"score must be 0-{MAX_SCORE}")
        return v

    @property
    def is_weak(self) -> bool:
        return self.score <= WEAK_SCORE_THRESHOLD


class InterviewLog(BaseModel):
    """One interview's debrief."""

    company: str
    role: str | None = None
    interview_date: date | None = None
    answered: list[AnsweredQuestion] = Field(default_factory=list)
    # Questions that surfaced that you hadn't predicted — add these to the bank.
    new_questions: list[str] = Field(default_factory=list)

    @property
    def average_score(self) -> float | None:
        if not self.answered:
            return None
        return round(sum(a.score for a in self.answered) / len(self.answered), 1)

    def weakest(self, n: int = 3) -> list[AnsweredQuestion]:
        """The lowest-scoring answers — what to rewrite first."""
        return sorted(self.answered, key=lambda a: a.score)[:n]

    def answers_to_rewrite(self) -> list[AnsweredQuestion]:
        """Every answer at or below the weak threshold."""
        return [a for a in self.answered if a.is_weak]

    def questions_to_add(self) -> list[str]:
        """New questions to fold into the question bank for next time."""
        return list(self.new_questions)
