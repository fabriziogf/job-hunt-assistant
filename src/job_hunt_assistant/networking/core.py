"""Networking & Referral Assistant — deterministic core (Chapter 4).

Chapter 4's thesis: you don't need a connection, you need a connection to a
connection — and the magic reframe is to **ask for advice, not a job** (the
moment you ask for a job you become a problem to solve). This module holds the
chapter's reusable, no-LLM pieces: the five advice questions, the outreach
template, the meeting etiquette, where to find a first connection, and a linter
that checks an outreach draft follows the "ask for advice" playbook.
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from job_hunt_assistant.findings import Finding, FindingsReport, Severity

# Keep first-touch outreach short — you're asking for 15 minutes.
MAX_OUTREACH_WORDS = 120


class OutreachContact(BaseModel):
    """Someone you want advice from (a connection, or a connection-to-a-connection)."""

    name: str
    title: str | None = None
    company: str | None = None
    mutual_connection: str | None = None
    # The genuine "coincidence" hook — a real shared detail to open with.
    coincidence: str | None = None


# The five advice questions that get people hired (Chapter 4).
ADVICE_QUESTIONS: list[str] = [
    "How did you get your job?",
    "What advice would you give someone trying to get into your field or company?",
    "What parts of your company are hiring right now?",
    "Could you refer me to the recruiter?",
    "Do you know someone else who could give me advice?",
]

# Etiquette once they say yes to meeting (Chapter 4).
MEETING_ETIQUETTE: list[str] = [
    "Show up prepared.",
    "End on time — if you said 15 minutes, end at 14.",
    "Ask 2 specific questions, not 'any advice?'.",
    "Send a thank-you within 24 hours, referencing one specific thing they said.",
    "Follow up a month later with what you did with their advice.",
]

# Where to find a first connection if you have no network (Chapter 4).
WHERE_TO_FIND: list[str] = [
    "Industry meetups (search Eventbrite or Meetup for your city + field).",
    "LinkedIn comments — comment thoughtfully on posts from people in your target role.",
    "Slack or Discord communities — join three, be useful in two.",
    "Alumni groups — built for exactly this.",
]


def outreach_template(
    *,
    name: str,
    coincidence: str,
    field: str,
    your_name: str,
    your_contact: str | None = None,
) -> str:
    """Fill the Chapter 4 outreach template (ask for advice, open with a hook)."""
    lines = [
        f"Hi {name} —",
        "",
        coincidence.rstrip("."),
        f"I'm exploring a move into {field}.",
        "Would you be open to a 15-minute call? I'd love your advice on how you "
        "got started.",
        "Either way — thanks for the inspiration.",
        "",
        your_name,
    ]
    if your_contact:
        lines.append(your_contact)
    return "\n".join(lines)


# Phrases that signal asking for a job rather than advice.
_JOB_ASK_RE = re.compile(
    r"\b(a job|are you hiring|hire me|give me a job|job opening|open positions?|"
    r"open roles?|any openings|apply for the|consider me for)\b",
    re.IGNORECASE,
)
_COINCIDENCE_RE = re.compile(
    r"\b(i noticed|i saw|i read|i came across|we both|we met|you wrote|your (post|talk|article))\b",
    re.IGNORECASE,
)
_GENERIC_OPENER_RE = re.compile(r"you don'?t know me", re.IGNORECASE)


def lint_outreach(
    message: str, *, contact: OutreachContact | None = None
) -> FindingsReport:
    """Check an outreach draft follows the Chapter 4 "ask for advice" playbook."""
    findings: list[Finding] = []
    lower = message.lower()

    if _JOB_ASK_RE.search(message):
        findings.append(
            Finding(
                code="asks_for_job",
                severity=Severity.WARNING,
                message="This reads like asking for a job. Ask for advice instead "
                "— the moment you ask for a job you become a problem to solve.",
                chapter=4,
            )
        )
    if _GENERIC_OPENER_RE.search(message):
        findings.append(
            Finding(
                code="generic_opener",
                severity=Severity.WARNING,
                message="'You don't know me, but...' is weak. Open with a genuine "
                "coincidence: 'I noticed...' beats it every time.",
                chapter=4,
            )
        )
    if not _COINCIDENCE_RE.search(message):
        findings.append(
            Finding(
                code="no_coincidence",
                severity=Severity.WARNING,
                message="No specific hook. Manufacture a coincidence — a post they "
                "wrote, a shared school, a mutual connection — to open the message.",
                chapter=4,
            )
        )
    if "advice" not in lower:
        findings.append(
            Finding(
                code="no_advice_ask",
                severity=Severity.INFO,
                message="Ask explicitly for advice — it's the reframe that gets a yes.",
                chapter=4,
            )
        )
    if len(message.split()) > MAX_OUTREACH_WORDS:
        findings.append(
            Finding(
                code="too_long",
                severity=Severity.INFO,
                message=f"Over ~{MAX_OUTREACH_WORDS} words — keep a first message "
                "short; you're only asking for 15 minutes.",
                chapter=4,
            )
        )

    return FindingsReport(findings=findings)
