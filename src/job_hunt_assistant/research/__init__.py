"""Company research capability (feeds the Cover Letter Writer and beyond)."""

from job_hunt_assistant.research.company import (
    CompanyFact,
    CompanyResearch,
    FactCategory,
    ManualResearchProvider,
    ResearchProvider,
)
from job_hunt_assistant.research.web import WebResearchProvider

__all__ = [
    "CompanyFact",
    "CompanyResearch",
    "FactCategory",
    "ManualResearchProvider",
    "ResearchProvider",
    "WebResearchProvider",
]
