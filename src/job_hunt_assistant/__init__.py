"""Job Hunt Assistant — an AI agent grounded in Laszlo Bock's *Apply Within* playbook."""

from job_hunt_assistant.findings import Finding, FindingsReport, Severity
from job_hunt_assistant.playbook import (
    PLAYBOOK,
    AgentSkill,
    ChapterPrinciples,
    Playbook,
)
from job_hunt_assistant.profile import (
    Achievement,
    CandidateProfile,
    Contact,
    Education,
    Experience,
    Skill,
)
from job_hunt_assistant.discovery import (
    JobMatch,
    JobPosting,
    JobSource,
    ManualJobSource,
    WebJobSource,
    match_job,
    rank_jobs,
)
from job_hunt_assistant.orchestration import (
    ApplicationOrchestrator,
    ApplicationPackage,
)
from job_hunt_assistant.research import (
    CompanyFact,
    CompanyResearch,
    FactCategory,
    ManualResearchProvider,
    ResearchProvider,
    WebResearchProvider,
)
from job_hunt_assistant.samples import load_profile, load_sample_profile

__all__ = [
    # Profile store
    "Achievement",
    "CandidateProfile",
    "Contact",
    "Education",
    "Experience",
    "Skill",
    # Playbook loader
    "PLAYBOOK",
    "Playbook",
    "AgentSkill",
    "ChapterPrinciples",
    # Shared findings
    "Finding",
    "FindingsReport",
    "Severity",
    # Company research
    "CompanyFact",
    "CompanyResearch",
    "FactCategory",
    "ManualResearchProvider",
    "ResearchProvider",
    "WebResearchProvider",
    # Job discovery + orchestration (Phase 5)
    "JobPosting",
    "JobMatch",
    "match_job",
    "rank_jobs",
    "JobSource",
    "ManualJobSource",
    "WebJobSource",
    "ApplicationOrchestrator",
    "ApplicationPackage",
    # Sample / profile loaders
    "load_profile",
    "load_sample_profile",
]
