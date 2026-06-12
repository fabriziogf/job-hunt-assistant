"""Structured cover letter / outbound email model (Chapter 3)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class LetterFormat(str, Enum):
    """A formal cover letter, or the modern equivalent: an outbound email.

    Chapter 3: "Your outbound email is your cover letter" — same principles, so
    one model serves both. EMAIL adds a subject line and a lighter register.
    """

    LETTER = "letter"
    EMAIL = "email"


class CoverLetter(BaseModel):
    """A four-paragraph cover letter or outbound email."""

    format: LetterFormat = LetterFormat.LETTER
    subject: str | None = None  # EMAIL only
    salutation: str = ""
    paragraphs: list[str] = Field(default_factory=list)
    signoff: str = ""

    def body_text(self) -> str:
        return "\n\n".join(self.paragraphs)

    def full_text(self) -> str:
        parts: list[str] = []
        if self.format is LetterFormat.EMAIL and self.subject:
            parts.append(f"Subject: {self.subject}")
        if self.salutation:
            parts.append(self.salutation)
        parts.append(self.body_text())
        if self.signoff:
            parts.append(self.signoff)
        return "\n\n".join(parts) + "\n"
