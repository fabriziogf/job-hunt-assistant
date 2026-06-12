"""Networking & Referral Assistant skill (Phase 4, Chapter 4)."""

from job_hunt_assistant.networking.core import (
    ADVICE_QUESTIONS,
    MAX_OUTREACH_WORDS,
    MEETING_ETIQUETTE,
    WHERE_TO_FIND,
    OutreachContact,
    lint_outreach,
    outreach_template,
)
from job_hunt_assistant.networking.writer import (
    OutreachMessage,
    OutreachWriter,
    build_outreach_prompt,
)

__all__ = [
    "OutreachContact",
    "ADVICE_QUESTIONS",
    "MEETING_ETIQUETTE",
    "WHERE_TO_FIND",
    "MAX_OUTREACH_WORDS",
    "outreach_template",
    "lint_outreach",
    "OutreachMessage",
    "OutreachWriter",
    "build_outreach_prompt",
]
