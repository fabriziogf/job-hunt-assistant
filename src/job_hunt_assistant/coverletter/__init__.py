"""Cover Letter / Outbound Email Writer skill (Phase 2, Chapter 3)."""

from job_hunt_assistant.coverletter.linter import (
    EXPECTED_PARAGRAPHS,
    MAX_WORDS,
    lint_cover_letter,
)
from job_hunt_assistant.coverletter.models import CoverLetter, LetterFormat
from job_hunt_assistant.coverletter.writer import (
    CoverLetterWriter,
    build_cover_letter_prompt,
)

__all__ = [
    "CoverLetter",
    "LetterFormat",
    "lint_cover_letter",
    "EXPECTED_PARAGRAPHS",
    "MAX_WORDS",
    "CoverLetterWriter",
    "build_cover_letter_prompt",
]
