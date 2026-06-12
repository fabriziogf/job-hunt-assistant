"""Resume assembler — ties the profile, linter, and rewriter into one Resume.

Takes a verified ``CandidateProfile`` (+ optional target job description) and
produces a structured, validated ``Resume``: selected and ordered experiences
with X/Y/Z bullets, threshold-filtered education, skills, and the linter's
findings attached so the user sees what to fix.

The selection / ordering / trimming logic here is **deterministic and fully
tested** — no LLM. The LLM rewriter is an *optional injected dependency*: when
provided it polishes each bullet, otherwise the assembler falls back to the
deterministic ``Achievement.to_xyz_bullet()``. So a resume can be assembled
(and tested) with no API key, and upgraded in place by passing a rewriter.

Chapter 2 rules applied at assembly time:
- Only *verified* achievements are included (honesty gate).
- Experiences are ordered most-recent-first; quantified bullets come first.
- Sub-3.5 GPAs are dropped from the output.
- The one-page-per-decade budget trims the weakest/oldest bullets.
- Brand names are carried through for recruiter keyword search.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from job_hunt_assistant.profile import Achievement, CandidateProfile, Contact
from job_hunt_assistant.resume.linter import (
    BULLETS_PER_PAGE,
    Finding,
    lint_profile,
    recommended_max_pages,
)
from job_hunt_assistant.resume.rewriter import ResumeRewriter


class ResumeBullet(BaseModel):
    text: str
    has_metric: bool


class ResumeExperience(BaseModel):
    company: str
    title: str
    location: str | None = None
    date_range: str
    bullets: list[ResumeBullet] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)


class ResumeEducation(BaseModel):
    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    graduation: date | None = None
    gpa: float | None = None  # populated only when it clears the Ch. 2 threshold
    awards: list[str] = Field(default_factory=list)


class Resume(BaseModel):
    """A finished, structured resume plus the linter findings behind it."""

    contact: Contact
    headline: str | None = None
    summary: str | None = None
    experiences: list[ResumeExperience] = Field(default_factory=list)
    education: list[ResumeEducation] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)

    def to_markdown(self) -> str:
        return _render_markdown(self)


_MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def _fmt_date(d: date) -> str:
    return f"{_MONTHS[d.month - 1]} {d.year}"


def _date_range(start: date, end: date | None) -> str:
    return f"{_fmt_date(start)} – {'Present' if end is None else _fmt_date(end)}"


def _ordered_achievements(achievements: list[Achievement]) -> list[Achievement]:
    """Verified only; quantified bullets first, original order otherwise (stable)."""
    verified = [a for a in achievements if a.verified]
    return sorted(verified, key=lambda a: not a.is_quantified)


def build_resume(
    profile: CandidateProfile,
    *,
    job_description: str | None = None,
    rewriter: ResumeRewriter | None = None,
    as_of: date | None = None,
) -> Resume:
    """Assemble a structured Resume from a verified candidate profile."""
    as_of = as_of or date.today()
    findings = lint_profile(profile, as_of=as_of).findings

    # Ch. 2 length budget: how many bullets fit in the page allowance.
    budget = recommended_max_pages(profile, as_of) * BULLETS_PER_PAGE

    # Most-recent-first; current roles ahead of past ones.
    experiences = sorted(
        profile.experiences, key=lambda e: (e.is_current, e.start), reverse=True
    )

    resume_experiences: list[ResumeExperience] = []
    remaining = budget
    for exp in experiences:
        if remaining <= 0:
            break
        kept = _ordered_achievements(exp.achievements)[:remaining]
        if not kept:
            continue
        remaining -= len(kept)
        bullets = [_make_bullet(a, job_description, rewriter) for a in kept]
        resume_experiences.append(
            ResumeExperience(
                company=exp.company,
                title=exp.title,
                location=exp.location,
                date_range=_date_range(exp.start, exp.end),
                bullets=bullets,
                brands=exp.brands,
            )
        )

    education = [
        ResumeEducation(
            institution=edu.institution,
            degree=edu.degree,
            field_of_study=edu.field_of_study,
            graduation=edu.graduation,
            # Ch. 2: only show a GPA that clears the threshold.
            gpa=edu.gpa if edu.gpa_meets_resume_threshold else None,
            awards=edu.awards,
        )
        for edu in profile.education
    ]

    return Resume(
        contact=profile.contact,
        headline=profile.headline,
        summary=profile.summary,
        experiences=resume_experiences,
        education=education,
        skills=[s.name for s in profile.skills],
        findings=findings,
    )


def _make_bullet(
    achievement: Achievement,
    job_description: str | None,
    rewriter: ResumeRewriter | None,
) -> ResumeBullet:
    if rewriter is not None:
        rewrite = rewriter.rewrite(achievement, job_description)
        return ResumeBullet(text=rewrite.rewritten, has_metric=rewrite.has_metric)
    # Deterministic fallback — no LLM.
    return ResumeBullet(
        text=achievement.to_xyz_bullet(), has_metric=achievement.is_quantified
    )


def _render_markdown(resume: Resume) -> str:
    c = resume.contact
    contact_bits = [c.email, c.phone, c.location, c.linkedin, c.website]
    contact_line = " | ".join(b for b in contact_bits if b)

    lines = [f"# {c.full_name}"]
    if contact_line:
        lines.append(contact_line)
    if resume.headline:
        lines.append(f"\n**{resume.headline}**")
    if resume.summary:
        lines.append(f"\n{resume.summary}")

    if resume.experiences:
        lines.append("\n## Experience")
        for exp in resume.experiences:
            loc = f" — {exp.location}" if exp.location else ""
            lines.append(f"\n### {exp.title}, {exp.company}{loc}")
            lines.append(f"*{exp.date_range}*")
            for b in exp.bullets:
                lines.append(f"- {b.text}")

    if resume.education:
        lines.append("\n## Education")
        for edu in resume.education:
            degree = ", ".join(p for p in [edu.degree, edu.field_of_study] if p)
            head = f"**{edu.institution}**" + (f" — {degree}" if degree else "")
            if edu.gpa is not None:
                head += f" (GPA {edu.gpa})"
            lines.append(f"\n{head}")
            for award in edu.awards:
                lines.append(f"- {award}")

    if resume.skills:
        lines.append("\n## Skills")
        lines.append(" • ".join(resume.skills))

    return "\n".join(lines) + "\n"
