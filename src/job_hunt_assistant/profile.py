"""Candidate profile store — the single source of truth for the whole agent.

Every skill (resume, cover letter, interview prep, negotiation) reads from this
model. The playbook's most-repeated rule is *don't lie, don't stretch*
(Ch. 2 & 8), so the design makes fabrication hard: an achievement only counts as
trustworthy when a human has marked it ``verified``. The agent surfaces and
sharpens real achievements — it never invents them.

Field choices are grounded in *Apply Within*:
- Achievements use the Ch. 2 formula: "Accomplished [X] as measured by [Y] by
  doing [Z]".
- ``brands`` captures recognizable company/tool names (Ch. 2: "name-drop every
  brand you can" — recruiters search their databases by company name).
- Education carries GPA + award + hardship context with the Ch. 2 disclosure
  rules baked into helper methods.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, field_validator

# Ch. 2: include a GPA only when it's 3.5+ (or top 10%); below that, leave it off.
RESUME_GPA_THRESHOLD = 3.5


class Contact(BaseModel):
    """Contact block. Ch. 2 requires this on *every* page of the resume."""

    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    website: str | None = None


class Achievement(BaseModel):
    """A single accomplishment in the Ch. 2 X/Y/Z formula.

    "Accomplished [X] as measured by [Y] by doing [Z]."

    - ``what`` (X): what you achieved — always required.
    - ``measured_by`` (Y): the number/%/$/time that quantifies it.
    - ``how`` (Z): how you actually did it.

    ``measured_by`` and ``how`` are optional because a raw profile entry may
    start incomplete; the Resume Builder's job is to push every bullet toward a
    fully-quantified X/Y/Z. ``is_quantified`` lets that skill flag the gaps.
    """

    what: str = Field(..., description="X — what you achieved")
    measured_by: str | None = Field(
        None, description="Y — how it was measured (numbers, %, $, time)"
    )
    how: str | None = Field(None, description="Z — how you actually did it")
    # Honesty gate: nothing is treated as resume-ready until a human confirms it.
    verified: bool = False
    tags: list[str] = Field(default_factory=list)

    @property
    def is_quantified(self) -> bool:
        """True when a measurable Y is present — the bar Ch. 2 sets for a bullet."""
        return self.measured_by is not None and self.measured_by.strip() != ""

    @property
    def is_complete(self) -> bool:
        """True when all three X/Y/Z parts are filled in."""
        return self.is_quantified and bool(self.how and self.how.strip())

    def to_xyz_bullet(self) -> str:
        """Render the achievement as a single resume-style bullet.

        Stitches together whatever of X/Y/Z is present. The phrasing is a
        starting point — the Resume Builder skill rewrites it into the
        candidate's voice.
        """
        parts = [self.what.rstrip(".")]
        if self.measured_by:
            parts.append(f"as measured by {self.measured_by.rstrip('.')}")
        if self.how:
            parts.append(f"by {self.how.rstrip('.')}")
        return " ".join(parts) + "."


class Experience(BaseModel):
    """A role at a company. ``end`` is None for the current position."""

    company: str
    title: str
    location: str | None = None
    start: date
    end: date | None = None
    achievements: list[Achievement] = Field(default_factory=list)
    # Ch. 2: recognizable brands the candidate worked with (clients, tools,
    # partners) — recruiters search by these names.
    brands: list[str] = Field(default_factory=list)

    @property
    def is_current(self) -> bool:
        return self.end is None

    @field_validator("end")
    @classmethod
    def _end_after_start(cls, v: date | None, info) -> date | None:
        start = info.data.get("start")
        if v is not None and start is not None and v < start:
            raise ValueError("end date cannot be before start date")
        return v


class Education(BaseModel):
    """An education entry with Ch. 2's GPA / award / hardship context.

    Hardship flags follow Ch. 2's "hardship rule": hardships help you get into
    college but generally *hurt* you getting a job — with three exceptions worth
    mentioning, captured here as explicit booleans.
    """

    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    graduation: date | None = None
    gpa: float | None = None
    gpa_scale: float = 4.0
    # Awards should describe what they were *for* (Ch. 2) — a bare trophy name
    # ("Won the Smith Prize") doesn't help.
    awards: list[str] = Field(default_factory=list)

    # The three Ch. 2 hardship exceptions worth surfacing:
    self_financed_third_plus: bool = False  # paid for 1/3+ of education (loans count)
    worked_during_school: bool = False
    first_generation: bool = False

    @property
    def gpa_meets_resume_threshold(self) -> bool:
        """Ch. 2: only show a GPA that's 3.5+ (on a 4.0 scale)."""
        if self.gpa is None:
            return False
        normalized = self.gpa / self.gpa_scale * 4.0
        return normalized >= RESUME_GPA_THRESHOLD

    @property
    def has_mentionable_hardship(self) -> bool:
        """True if any of the three Ch. 2 hardship exceptions applies."""
        return (
            self.self_financed_third_plus
            or self.worked_during_school
            or self.first_generation
        )


class Skill(BaseModel):
    """A skill. ``acronym_expansion`` supports the Ch. 2 ATS rule of spelling out
    an acronym once, e.g. name="SEO", acronym_expansion="Search Engine
    Optimization"."""

    name: str
    acronym_expansion: str | None = None
    category: str | None = None


class CandidateProfile(BaseModel):
    """The full verified profile. The agent's single source of truth."""

    contact: Contact
    headline: str | None = None
    summary: str | None = None
    experiences: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)

    # --- Convenience accessors used across skills -------------------------

    def all_achievements(self) -> list[Achievement]:
        return [a for exp in self.experiences for a in exp.achievements]

    def verified_achievements(self) -> list[Achievement]:
        """Only achievements a human has confirmed — the honest set to draw on."""
        return [a for a in self.all_achievements() if a.verified]

    def unquantified_achievements(self) -> list[Achievement]:
        """Verified achievements still missing a measurable Y — work for the
        Resume Builder to chase down."""
        return [a for a in self.verified_achievements() if not a.is_quantified]

    def all_brands(self) -> list[str]:
        """De-duplicated, order-preserving list of brand names across roles."""
        seen: dict[str, None] = {}
        for exp in self.experiences:
            for brand in [exp.company, *exp.brands]:
                if brand and brand not in seen:
                    seen[brand] = None
        return list(seen)

    # --- Persistence ------------------------------------------------------

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "CandidateProfile":
        return cls.model_validate_json(raw)
