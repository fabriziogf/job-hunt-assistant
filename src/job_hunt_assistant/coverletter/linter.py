"""Cover letter linter — the deterministic "first, do no harm" checks (Ch. 3).

Chapter 3's whole philosophy is defensive: a cover letter can't win the job, but
a handful of mistakes can lose it. This linter catches exactly those downside
risks — no LLM, so it's instant and fully tested:

- a generic "Dear Hiring Manager" salutation (~30% more likely to be rejected);
- a missing or placeholder company name (never copy-paste the wrong one);
- leftover template placeholders like ``[Company]`` or ``TODO``;
- a structure that isn't the four-paragraph shape;
- paragraph 3 not referencing anything company-specific (the only paragraph that
  proves you did the research);
- a referral not named in the first sentence (when you have one);
- a letter that runs long (more length = more chances to mess up).
"""

from __future__ import annotations

import re

from job_hunt_assistant.coverletter.models import CoverLetter
from job_hunt_assistant.findings import Finding, FindingsReport, Severity
from job_hunt_assistant.research.company import CompanyResearch

# A one-page cover letter is short; well over this many words is a red flag.
MAX_WORDS = 320
# The Chapter 3 structure is four paragraphs.
EXPECTED_PARAGRAPHS = 4

_GENERIC_SALUTATIONS = (
    "dear hiring manager",
    "to whom it may concern",
    "dear sir",
    "dear madam",
    "dear sir or madam",
    "dear recruiter",
)
_PLACEHOLDER_RE = re.compile(r"\[[^\]]+\]|\b(?:TODO|FIXME|XXX)\b")


def lint_cover_letter(
    letter: CoverLetter,
    *,
    company: str,
    referral: str | None = None,
    research: CompanyResearch | None = None,
) -> FindingsReport:
    """Run all deterministic Chapter 3 checks on a drafted cover letter."""
    findings: list[Finding] = []
    full = letter.full_text()
    full_lower = full.lower()

    findings += _check_salutation(letter, research)
    findings += _check_company_name(letter, company, full_lower)
    findings += _check_placeholders(full)
    findings += _check_structure(letter)
    findings += _check_customization(letter, company, research)
    findings += _check_referral(letter, referral)
    findings += _check_length(letter)

    return FindingsReport(findings=findings)


def _check_salutation(
    letter: CoverLetter, research: CompanyResearch | None
) -> list[Finding]:
    sal = letter.salutation.strip().lower()
    if any(g in sal for g in _GENERIC_SALUTATIONS):
        msg = (
            "Generic salutation — letters addressed 'Dear Hiring Manager' are "
            "~30% more likely to be rejected. Use the real hiring manager's name."
        )
        if research and research.hiring_manager_name:
            msg += f" You have it: {research.hiring_manager_name}."
        return [
            Finding(
                code="generic_salutation",
                severity=Severity.WARNING,
                message=msg,
                chapter=3,
            )
        ]
    return []


def _check_company_name(
    letter: CoverLetter, company: str, full_lower: str
) -> list[Finding]:
    if company.strip().lower() not in full_lower:
        return [
            Finding(
                code="missing_company_name",
                severity=Severity.ERROR,
                message=(
                    f"The target company '{company}' does not appear in the "
                    "letter. Triple-check it — a wrong/missing company name is an "
                    "instant reject."
                ),
                chapter=3,
            )
        ]
    return []


def _check_placeholders(full: str) -> list[Finding]:
    hits = _PLACEHOLDER_RE.findall(full)
    if hits:
        return [
            Finding(
                code="placeholder_text",
                severity=Severity.ERROR,
                message=(
                    "Unfilled placeholder(s) left in the letter "
                    f"({', '.join(sorted(set(h if isinstance(h, str) else h[0] for h in hits)))}). "
                    "Fill or remove before sending."
                ),
                chapter=3,
            )
        ]
    return []


def _check_structure(letter: CoverLetter) -> list[Finding]:
    n = len(letter.paragraphs)
    if n != EXPECTED_PARAGRAPHS:
        return [
            Finding(
                code="not_four_paragraphs",
                severity=Severity.WARNING,
                message=(
                    f"{n} paragraph(s); Chapter 3 prescribes four: intro, expand, "
                    "why-you-specifically, and a promise to follow up."
                ),
                chapter=3,
            )
        ]
    return []


def _check_customization(
    letter: CoverLetter, company: str, research: CompanyResearch | None
) -> list[Finding]:
    """Paragraph 3 must reference something specific to the company."""
    if len(letter.paragraphs) < 3:
        return []  # structure check already flagged this
    p3 = letter.paragraphs[2].lower()

    if research is None or not research.has_specifics:
        return [
            Finding(
                code="no_company_research",
                severity=Severity.WARNING,
                message=(
                    "No company-specific research available — paragraph 3 ('why "
                    "you, specifically') is the only one that proves you did the "
                    "homework. Add a recent product, statement, or news item."
                ),
                chapter=3,
            )
        ]

    # Does P3 echo any researched fact (a meaningful word from it) or the company?
    referenced = company.strip().lower() in p3
    for fact in research.facts:
        words = [w for w in re.findall(r"[a-z0-9]+", fact.text.lower()) if len(w) > 4]
        if any(w in p3 for w in words):
            referenced = True
            break
    if not referenced:
        return [
            Finding(
                code="p3_not_specific",
                severity=Severity.WARNING,
                message=(
                    "Paragraph 3 doesn't reference any researched specific. It's "
                    "the only paragraph that proves you researched the company — "
                    "weave in a concrete detail."
                ),
                chapter=3,
            )
        ]
    return []


def _check_referral(letter: CoverLetter, referral: str | None) -> list[Finding]:
    if not referral:
        return []
    first = letter.paragraphs[0].lower() if letter.paragraphs else ""
    if referral.strip().lower() not in first:
        return [
            Finding(
                code="referral_not_in_first_sentence",
                severity=Severity.WARNING,
                message=(
                    f"You have a referral ({referral}) but it isn't named in the "
                    "first sentence — that recognizable name is the strongest "
                    "reason to keep reading."
                ),
                chapter=3,
            )
        ]
    return []


def _check_length(letter: CoverLetter) -> list[Finding]:
    words = len(letter.body_text().split())
    if words > MAX_WORDS:
        return [
            Finding(
                code="too_long",
                severity=Severity.WARNING,
                message=(
                    f"~{words} words — longer than a one-page letter needs. The "
                    "longer it is, the more chances to mess it up. Tighten it."
                ),
                chapter=3,
            )
        ]
    return []
