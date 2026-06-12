"""Company research — the specific, citable facts that power a cover letter.

Chapter 3 says paragraph 3 ("why you, specifically") is the only part of a cover
letter that proves you researched the company — a recent product launch, a CEO
statement, a new market, an industry challenge. This module models that research
as structured, *sourced* data and defines how a skill obtains it.

Design: research is obtained through a ``ResearchProvider`` interface. The only
implementation today is ``ManualResearchProvider`` (you supply the facts), which
keeps everything offline, testable, and — crucially — free of hallucinated facts
(wrong facts in a cover letter are exactly what gets it rejected). A live-web
provider can implement the same interface later without touching the writer.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class FactCategory(str, Enum):
    PRODUCT_LAUNCH = "product_launch"
    CEO_STATEMENT = "ceo_statement"
    NEWS = "news"
    MARKET = "market"
    INDUSTRY_CHALLENGE = "industry_challenge"
    OTHER = "other"


class CompanyFact(BaseModel):
    """One specific, sourced detail about a company.

    ``source``/``url``/``date`` carry provenance so the writer can ground
    paragraph 3 in something real and the candidate can verify it before sending.
    """

    text: str
    category: FactCategory = FactCategory.OTHER
    source: str | None = None
    url: str | None = None
    date: str | None = None  # free-form (e.g. "2026-05" or "last week")


class CompanyResearch(BaseModel):
    """Everything known about a target company for a single application."""

    company: str
    hiring_manager_name: str | None = None
    hiring_manager_title: str | None = None
    facts: list[CompanyFact] = Field(default_factory=list)

    @property
    def has_specifics(self) -> bool:
        """True if there's at least one concrete fact for paragraph 3."""
        return any(f.text.strip() for f in self.facts)

    def best_fact(self) -> CompanyFact | None:
        """The fact to feature in paragraph 3 (the first provided one)."""
        return self.facts[0] if self.facts else None


@runtime_checkable
class ResearchProvider(Protocol):
    """How a skill obtains company research. Swap implementations freely."""

    def research(self, company: str) -> CompanyResearch: ...


class ManualResearchProvider:
    """Research supplied by hand. The offline, no-hallucination default.

    Holds a set of ``CompanyResearch`` objects keyed by company name
    (case-insensitive). Lookups for an unknown company raise ``KeyError`` rather
    than inventing facts.
    """

    def __init__(self, entries: list[CompanyResearch] | None = None) -> None:
        self._by_company: dict[str, CompanyResearch] = {}
        for entry in entries or []:
            self.add(entry)

    def add(self, research: CompanyResearch) -> None:
        self._by_company[research.company.strip().lower()] = research

    def research(self, company: str) -> CompanyResearch:
        try:
            return self._by_company[company.strip().lower()]
        except KeyError:
            raise KeyError(
                f"No manual research for {company!r}. Add a CompanyResearch entry "
                "(the agent never invents company facts)."
            ) from None
