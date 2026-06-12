"""Resume linter — deterministic checks against the playbook's resume rules.

This module contains *no LLM calls*. It inspects a ``CandidateProfile`` and emits
structured, chapter-cited findings for the rules from Chapter 2 ("Your resume in
one formula") and Chapter 3's "first, do no harm" mindset that can be evaluated by
pure logic: quantification gaps, the GPA threshold, award context, length budget,
contact reachability, and the honesty gate.

Keeping these checks deterministic means they are fast, free, fully unit-tested,
and run before any model is invoked. The LLM rewriter (separate module) handles
the judgement calls — polishing bullets and catching typos.
"""

from __future__ import annotations

import math
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field

from job_hunt_assistant.profile import CandidateProfile


class Severity(str, Enum):
    """How much a finding matters.

    - ERROR: something the playbook says actively gets you rejected.
    - WARNING: a rule violation worth fixing before sending.
    - INFO: an observation or opportunity (e.g. brands you could name-drop).
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Finding(BaseModel):
    """A single linter result, traceable back to a playbook chapter."""

    code: str
    severity: Severity
    message: str
    chapter: int
    where: str | None = None  # human-readable location, e.g. "Amazon — Launched..."


class LintReport(BaseModel):
    """The full set of findings for one profile."""

    findings: list[Finding] = Field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def by_code(self, code: str) -> list[Finding]:
        return [f for f in self.findings if f.code == code]


# Chapter 2: a resume should run one page per decade of experience.
YEARS_PER_PAGE = 10
# Rough rendering heuristic: how many achievement bullets fit on a page.
BULLETS_PER_PAGE = 14
# Awards shorter than this (in words) probably lack the "for what?" context Ch. 2
# asks for ("Won the Smith Prize" — for what?).
AWARD_CONTEXT_MIN_WORDS = 4


def _years_of_experience(profile: CandidateProfile, as_of: date) -> float:
    """Span from the earliest role start to ``as_of``, in years."""
    starts = [exp.start for exp in profile.experiences]
    if not starts:
        return 0.0
    return max(0.0, (as_of - min(starts)).days / 365.25)


def recommended_max_pages(profile: CandidateProfile, as_of: date | None = None) -> int:
    """Ch. 2: one page per decade (<10 yrs -> 1 page), minimum 1."""
    as_of = as_of or date.today()
    years = _years_of_experience(profile, as_of)
    return max(1, math.ceil(years / YEARS_PER_PAGE))


def lint_profile(
    profile: CandidateProfile, as_of: date | None = None
) -> LintReport:
    """Run all deterministic resume checks and return a report."""
    as_of = as_of or date.today()
    findings: list[Finding] = []

    findings += _check_quantification(profile)
    findings += _check_gpa_threshold(profile)
    findings += _check_award_context(profile)
    findings += _check_length(profile, as_of)
    findings += _check_contact(profile)
    findings += _check_honesty_gate(profile)
    findings += _check_brand_opportunities(profile)

    return LintReport(findings=findings)


# --- individual checks --------------------------------------------------------


def _loc(company: str, what: str) -> str:
    snippet = what if len(what) <= 50 else what[:47] + "..."
    return f"{company} — {snippet}"


def _check_quantification(profile: CandidateProfile) -> list[Finding]:
    """Ch. 2: every bullet needs a measurable Y. Flag verified ones that lack it."""
    out: list[Finding] = []
    for exp in profile.experiences:
        for a in exp.achievements:
            if a.verified and not a.is_quantified:
                out.append(
                    Finding(
                        code="missing_metric",
                        severity=Severity.WARNING,
                        message=(
                            "Achievement has no measurable result (Y). Add a "
                            "number, %, $, or time to complete the X/Y/Z formula."
                        ),
                        chapter=2,
                        where=_loc(exp.company, a.what),
                    )
                )
    return out


def _check_gpa_threshold(profile: CandidateProfile) -> list[Finding]:
    """Ch. 2: only show a GPA of 3.5+; below that, leave it off."""
    out: list[Finding] = []
    for edu in profile.education:
        if edu.gpa is not None and not edu.gpa_meets_resume_threshold:
            out.append(
                Finding(
                    code="gpa_below_threshold",
                    severity=Severity.WARNING,
                    message=(
                        f"GPA {edu.gpa} is below the 3.5 bar — omit it from the "
                        "resume (or slice it, e.g. a higher in-major GPA, and "
                        "disclose that)."
                    ),
                    chapter=2,
                    where=edu.institution,
                )
            )
    return out


def _check_award_context(profile: CandidateProfile) -> list[Finding]:
    """Ch. 2: describe what an award was *for*; a bare name doesn't help."""
    out: list[Finding] = []
    for edu in profile.education:
        for award in edu.awards:
            if len(award.split()) < AWARD_CONTEXT_MIN_WORDS:
                out.append(
                    Finding(
                        code="award_lacks_context",
                        severity=Severity.INFO,
                        message=(
                            f"Award '{award}' may lack context — say what it was "
                            "for and how selective it was."
                        ),
                        chapter=2,
                        where=edu.institution,
                    )
                )
    return out


def _check_length(profile: CandidateProfile, as_of: date) -> list[Finding]:
    """Ch. 2: one page per decade; warn if the bullet count likely overflows."""
    out: list[Finding] = []
    max_pages = recommended_max_pages(profile, as_of)
    total_bullets = sum(len(exp.achievements) for exp in profile.experiences)
    budget = max_pages * BULLETS_PER_PAGE
    if total_bullets > budget:
        out.append(
            Finding(
                code="likely_too_long",
                severity=Severity.WARNING,
                message=(
                    f"{total_bullets} bullets likely exceed the {max_pages}-page "
                    f"budget (~{budget} bullets). Cut the weakest bullets — one "
                    "page per decade of experience."
                ),
                chapter=2,
            )
        )
    return out


def _check_contact(profile: CandidateProfile) -> list[Finding]:
    """Ch. 2 wants you findable. At minimum an email should be present."""
    out: list[Finding] = []
    c = profile.contact
    if not c.email:
        out.append(
            Finding(
                code="missing_email",
                severity=Severity.ERROR,
                message="No email on the profile — a recruiter can't reach you.",
                chapter=2,
                where=c.full_name,
            )
        )
    if not c.phone:
        out.append(
            Finding(
                code="missing_phone",
                severity=Severity.INFO,
                message="No phone number — consider adding one for reachability.",
                chapter=2,
                where=c.full_name,
            )
        )
    return out


def _check_honesty_gate(profile: CandidateProfile) -> list[Finding]:
    """Ch. 2: never fabricate. Unverified achievements are excluded until a human
    confirms them — surface how many are being held back."""
    out: list[Finding] = []
    unverified = [a for a in profile.all_achievements() if not a.verified]
    if unverified:
        out.append(
            Finding(
                code="unverified_excluded",
                severity=Severity.INFO,
                message=(
                    f"{len(unverified)} achievement(s) are unverified and will be "
                    "excluded from the resume until you confirm them. The agent "
                    "never fabricates — verify real ones to include them."
                ),
                chapter=2,
            )
        )
    return out


def _check_brand_opportunities(profile: CandidateProfile) -> list[Finding]:
    """Ch. 2: name-drop recognizable brands — recruiters search by company name."""
    out: list[Finding] = []
    brands = profile.all_brands()
    if brands:
        out.append(
            Finding(
                code="brands_available",
                severity=Severity.INFO,
                message=(
                    "Recognizable brands to surface (recruiters search by name): "
                    + ", ".join(brands)
                ),
                chapter=2,
            )
        )
    return out
