"""LLM cover letter / outbound email writer (Chapter 3).

Generates the four-paragraph structure — intro, expand, why-you-specifically,
promise to follow up — grounded in the playbook and in *provided* company
research. Honesty is the hard constraint: the model may only use company facts
from the supplied research (never invented), only experience from the candidate
profile, and the real hiring-manager name when one is known.

Same testable shape as the resume rewriter: prompt construction is a pure
function, and the Anthropic client is injected so tests run with a fake.
"""

from __future__ import annotations

from typing import Protocol

from job_hunt_assistant.coverletter.models import CoverLetter, LetterFormat
from job_hunt_assistant.playbook import PLAYBOOK, AgentSkill
from job_hunt_assistant.profile import CandidateProfile
from job_hunt_assistant.research.company import CompanyResearch

MODEL = "claude-opus-4-8"
MAX_TOKENS = 1500

_HONESTY_RULES = """\
Hard rules, in priority order:
1. NEVER invent facts about the company. Use ONLY the provided research for any
   company-specific claim in paragraph 3. If no research is provided, keep
   paragraph 3 honest and general rather than fabricating a detail.
2. NEVER claim experience the candidate profile does not contain.
3. Address the letter to the real hiring manager by name when one is provided.
   If no name is available, address it to the specific team or role — never to
   "Dear Hiring Manager" or "To Whom It May Concern".
4. Structure: exactly four paragraphs.
   - P1: one sentence — who you are, the role, and any referral (name the
     referral in this first sentence if provided).
   - P2: three sentences max — build on the intro; do NOT repeat the resume.
   - P3: three sentences max — why you, specifically; reference a concrete
     researched detail about THIS company.
   - P4: a brief promise to follow up.
5. Always spell the company name correctly and exactly as given.
6. Keep it short — a one-page letter. Brevity reduces the chance of mistakes."""


def _profile_brief(profile: CandidateProfile) -> str:
    """A compact, honest snapshot of the candidate for grounding (verified only)."""
    lines = [f"Name: {profile.contact.full_name}"]
    if profile.headline:
        lines.append(f"Headline: {profile.headline}")
    if profile.summary:
        lines.append(f"Summary: {profile.summary}")
    verified = profile.verified_achievements()
    if verified:
        lines.append("Selected verified achievements:")
        for a in verified[:5]:
            lines.append(f"- {a.to_xyz_bullet()}")
    return "\n".join(lines)


def build_cover_letter_prompt(
    profile: CandidateProfile,
    *,
    company: str,
    role: str,
    job_description: str | None = None,
    research: CompanyResearch | None = None,
    referral: str | None = None,
    fmt: LetterFormat = LetterFormat.LETTER,
) -> tuple[str, str]:
    """Build the (system, user) prompt. Pure — no API call."""
    fmt_note = (
        "Write a formal cover letter."
        if fmt is LetterFormat.LETTER
        else "Write a concise outbound prospecting EMAIL (include a short, "
        "specific subject line). Same four-paragraph principles, lighter register."
    )
    system = "\n\n".join([PLAYBOOK.as_prompt(AgentSkill.COVER_LETTER), _HONESTY_RULES])

    parts = [
        fmt_note,
        "",
        f"TARGET: {role} at {company}",
        "",
        "CANDIDATE (use only this for experience claims):",
        _profile_brief(profile),
    ]
    if referral:
        parts += ["", f"REFERRAL (name in the first sentence): {referral}"]
    if job_description:
        parts += ["", "JOB DESCRIPTION:", job_description.strip()]
    if research and research.has_specifics:
        parts += ["", "COMPANY RESEARCH (the ONLY source for company-specific claims):"]
        if research.hiring_manager_name:
            title = f", {research.hiring_manager_title}" if research.hiring_manager_title else ""
            parts.append(f"- Hiring manager: {research.hiring_manager_name}{title}")
        for fact in research.facts:
            src = f" (source: {fact.source})" if fact.source else ""
            parts.append(f"- {fact.text}{src}")
    else:
        parts += [
            "",
            "COMPANY RESEARCH: none provided — keep paragraph 3 honest and "
            "general; do NOT invent a company detail.",
        ]
    return system, "\n".join(parts)


class SupportsParse(Protocol):
    @property
    def messages(self) -> object: ...


class CoverLetterWriter:
    """Drafts cover letters / outbound emails via Claude.

    Pass a client for testing; otherwise it lazily builds the default
    ``anthropic.Anthropic()`` (reads ``ANTHROPIC_API_KEY``).
    """

    def __init__(self, client: SupportsParse | None = None) -> None:
        self._client = client

    def _get_client(self) -> SupportsParse:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def write(
        self,
        profile: CandidateProfile,
        *,
        company: str,
        role: str,
        job_description: str | None = None,
        research: CompanyResearch | None = None,
        referral: str | None = None,
        fmt: LetterFormat = LetterFormat.LETTER,
    ) -> CoverLetter:
        system, user = build_cover_letter_prompt(
            profile,
            company=company,
            role=role,
            job_description=job_description,
            research=research,
            referral=referral,
            fmt=fmt,
        )
        response = self._get_client().messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=CoverLetter,
        )
        letter = response.parsed_output
        letter.format = fmt  # ensure the requested format is recorded
        return letter
