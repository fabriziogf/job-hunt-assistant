"""Application Pipeline Tracker — deterministic (Chapter 7).

Chapter 7 reframes applying as the *finish* line, run as a volume game with a
simple tracker. This module encodes that chapter directly — no LLM:

- the six-column application record (company, role, contact, date applied,
  status, last touch);
- the volume math (~100 applications -> ~5 first rounds -> ~1-2 finals -> ~1
  offer);
- the follow-up cadence (every 2 weeks, for 6 weeks);
- B-tier-first sequencing (an offer there is leverage with the A companies);
- the tactical rules (apply direct, always PDF, multiple roles per company,
  reapply after 3 months of silence).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel, Field

# Chapter 7 follow-up cadence.
FOLLOWUP_INTERVAL_DAYS = 14  # every 2 weeks
FOLLOWUP_WINDOW_DAYS = 42  # for 6 weeks
# Reapply after 3 months of silence.
REAPPLY_AFTER_DAYS = 90

# Chapter 7 volume ratios, normalized per application (100 -> 5 -> 1.5 -> 1).
FIRST_ROUND_RATE = 0.05
FINAL_ROUND_RATE = 0.015
OFFER_RATE = 0.01


class ApplicationStatus(str, Enum):
    APPLIED = "applied"
    INTERVIEWED = "interviewed"
    FINAL_ROUND = "final_round"
    OFFER = "offer"
    CLOSED = "closed"


# Statuses where you're still awaiting a response (follow-up applies).
_OPEN_STATUSES = {
    ApplicationStatus.APPLIED,
    ApplicationStatus.INTERVIEWED,
    ApplicationStatus.FINAL_ROUND,
}


class CompanyTier(str, Enum):
    """A = dream, B = middle (start here), C = easy lateral / fallback."""

    A = "a"
    B = "b"
    C = "c"


# Chapter 7: start with B-tier companies, then A, then C.
_TIER_PRIORITY = {CompanyTier.B: 0, CompanyTier.A: 1, CompanyTier.C: 2}


class Application(BaseModel):
    """One row of the six-column tracker."""

    company: str
    role: str
    contact: str | None = None
    date_applied: date
    status: ApplicationStatus = ApplicationStatus.APPLIED
    last_touch: date | None = None  # defaults to date_applied
    tier: CompanyTier = CompanyTier.B

    def _last_touch(self) -> date:
        return self.last_touch or self.date_applied

    @property
    def is_open(self) -> bool:
        return self.status in _OPEN_STATUSES

    def followup_due(self, as_of: date) -> bool:
        """True if it's time to follow up (Chapter 7 cadence)."""
        if not self.is_open:
            return False
        within_window = (as_of - self.date_applied).days <= FOLLOWUP_WINDOW_DAYS
        since_touch = (as_of - self._last_touch()).days >= FOLLOWUP_INTERVAL_DAYS
        return within_window and since_touch

    def should_reapply(self, as_of: date) -> bool:
        """Chapter 7: if silent after ~3 months, refresh the resume and reapply."""
        return (
            self.status == ApplicationStatus.APPLIED
            and (as_of - self.date_applied).days >= REAPPLY_AFTER_DAYS
        )


class FunnelProjection(BaseModel):
    applications: int
    expected_first_rounds: float
    expected_final_rounds: float
    expected_offers: float

    def summary(self) -> str:
        return (
            f"{self.applications} applications -> "
            f"~{self.expected_first_rounds:.0f} first rounds -> "
            f"~{self.expected_final_rounds:.1f} finals -> "
            f"~{self.expected_offers:.1f} offers."
        )


def project_funnel(num_applications: int) -> FunnelProjection:
    """Project the Chapter 7 funnel from a number of applications."""
    return FunnelProjection(
        applications=num_applications,
        expected_first_rounds=round(num_applications * FIRST_ROUND_RATE, 1),
        expected_final_rounds=round(num_applications * FINAL_ROUND_RATE, 1),
        expected_offers=round(num_applications * OFFER_RATE, 1),
    )


def applications_needed(target_offers: int = 1) -> int:
    """How many applications a target number of offers implies (~100 per offer)."""
    return math.ceil(target_offers / OFFER_RATE)


def recommended_application_order(
    applications: list[Application],
) -> list[Application]:
    """Order targets B-tier first (then A, then C), recent first within a tier."""
    return sorted(
        applications,
        key=lambda a: (_TIER_PRIORITY[a.tier], -a.date_applied.toordinal()),
    )


# The follow-up message Chapter 7 suggests.
FOLLOWUP_MESSAGE = (
    "I hope you won't mind my persistence — I care deeply about this company. "
    "Just wanted to confirm my application is still on your list to review."
)

# Tactical rules from Chapter 7.
TACTICAL_TIPS: list[str] = [
    "Apply directly on the company's site, not third-party portals.",
    "Always submit a PDF, never a Word doc.",
    "Apply to multiple roles at the same company — different recruiters screen each.",
    "If silent after 3 months, refresh your resume and reapply.",
]


class Pipeline(BaseModel):
    """A collection of applications with funnel and follow-up helpers."""

    applications: list[Application] = Field(default_factory=list)

    def add(self, application: Application) -> None:
        self.applications.append(application)

    def counts_by_status(self) -> dict[ApplicationStatus, int]:
        counts = {s: 0 for s in ApplicationStatus}
        for app in self.applications:
            counts[app.status] += 1
        return counts

    def open_applications(self) -> list[Application]:
        return [a for a in self.applications if a.is_open]

    def due_followups(self, as_of: date) -> list[Application]:
        return [a for a in self.applications if a.followup_due(as_of)]

    def needing_reapply(self, as_of: date) -> list[Application]:
        return [a for a in self.applications if a.should_reapply(as_of)]

    def projection(self) -> FunnelProjection:
        """Project offers from the number of applications submitted so far."""
        return project_funnel(len(self.applications))
