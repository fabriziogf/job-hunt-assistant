"""Job discovery & matching (extends beyond the literal playbook).

The guide assumes you already have jobs to apply to; this module adds the step
of *finding the right ones*. A ``JobPosting`` is scored against the candidate by
reusing the Phase 1 machinery — assemble the candidate's resume, then run the
ATS keyword match against the posting. That gives a fit score, the gaps, and a
ranking, which feeds the rest of the flow (which jobs to prioritize, and the
keyword gaps the cover letter / resume should address).

Postings are supplied (manual now), mirroring the company-research design: a
live-scraping source can be added later without changing the matcher.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from job_hunt_assistant.ats import TARGET_MATCH, score_resume
from job_hunt_assistant.pipeline.core import CompanyTier
from job_hunt_assistant.profile import CandidateProfile
from job_hunt_assistant.resume import build_resume


class JobPosting(BaseModel):
    """A role to potentially apply to."""

    company: str
    role: str
    description: str
    location: str | None = None
    url: str | None = None
    # The candidate's own A/B/C framing (dream / middle / fallback), not fit.
    tier: CompanyTier = CompanyTier.B


class JobMatch(BaseModel):
    """How well the candidate fits one posting."""

    job: JobPosting
    score: float  # ATS-style keyword match, 0-100
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)

    @property
    def recommended(self) -> bool:
        """Meets the Chapter 2 ATS target — a strong, worth-tailoring fit."""
        return self.score >= TARGET_MATCH


def match_job(
    profile: CandidateProfile, job: JobPosting, *, as_of: date | None = None
) -> JobMatch:
    """Score a candidate against a posting by reusing resume + ATS scoring."""
    resume = build_resume(profile, as_of=as_of)
    report = score_resume(resume, job.description)
    return JobMatch(
        job=job,
        score=report.score,
        matched_keywords=report.matched,
        missing_keywords=report.missing[:15],
    )


def rank_jobs(
    profile: CandidateProfile, jobs: list[JobPosting], *, as_of: date | None = None
) -> list[JobMatch]:
    """Rank postings best-fit first."""
    matches = [match_job(profile, j, as_of=as_of) for j in jobs]
    return sorted(matches, key=lambda m: m.score, reverse=True)
