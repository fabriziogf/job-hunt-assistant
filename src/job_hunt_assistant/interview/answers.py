"""Answer model + the deterministic structure check (Chapter 6).

Chapter 6 gives one structure for every answer:
  1. Restate the question (buys 3 seconds to think).
  2. Preview what you're about to say.
  3. Tell a specific story illustrating the trait (with numbers when possible).
  4. Summarize the point again.
"Tell them what you'll say. Say it. Tell them what you said."

The ``Answer`` model encodes those four parts as fields, so the structure is
inherent. ``lint_answer()`` then checks completeness and quality — that no part
is empty and that the story is specific (ideally quantified) — and emits
chapter-cited findings, no LLM required.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from job_hunt_assistant.findings import Finding, FindingsReport, Severity

# A story should be substantive but not a monologue.
STORY_MIN_WORDS = 12
STORY_MAX_WORDS = 220


class Answer(BaseModel):
    """One answer in the Chapter 6 four-part structure."""

    restate: str = ""
    preview: str = ""
    story: str = ""
    summary: str = ""
    # Which verified achievement the story draws on (honesty traceability).
    achievement_tag: str | None = None

    def to_text(self) -> str:
        return " ".join(
            part.strip()
            for part in (self.restate, self.preview, self.story, self.summary)
            if part.strip()
        )


def _has_number(text: str) -> bool:
    return re.search(r"\d", text) is not None


def lint_answer(answer: Answer) -> FindingsReport:
    """Check an answer follows the four-part structure and is specific."""
    findings: list[Finding] = []

    parts = {
        "restate": answer.restate,
        "preview": answer.preview,
        "story": answer.story,
        "summary": answer.summary,
    }
    for name, value in parts.items():
        if not value.strip():
            findings.append(
                Finding(
                    code=f"missing_{name}",
                    severity=Severity.WARNING,
                    message=(
                        f"Answer is missing the '{name}' part of the four-part "
                        "structure (restate -> preview -> story -> summarize)."
                    ),
                    chapter=6,
                )
            )

    story_words = len(answer.story.split())
    if answer.story.strip() and not _has_number(answer.story):
        findings.append(
            Finding(
                code="story_not_quantified",
                severity=Severity.INFO,
                message="Story has no numbers — make it specific with a metric "
                "where possible (Chapter 6).",
                chapter=6,
            )
        )
    if 0 < story_words < STORY_MIN_WORDS:
        findings.append(
            Finding(
                code="story_too_thin",
                severity=Severity.INFO,
                message=f"Story is only {story_words} words — flesh out the "
                "specific situation and result.",
                chapter=6,
            )
        )
    if story_words > STORY_MAX_WORDS:
        findings.append(
            Finding(
                code="story_too_long",
                severity=Severity.INFO,
                message=f"Story is ~{story_words} words — tighten it so the point "
                "lands before the interviewer drifts.",
                chapter=6,
            )
        )

    return FindingsReport(findings=findings)


class AnswerSet(BaseModel):
    """The two answers Chapter 6 says to prepare per question.

    A second interviewer who repeats a question gets your fresh, second answer.
    """

    question: str
    answers: list[Answer] = Field(default_factory=list)
