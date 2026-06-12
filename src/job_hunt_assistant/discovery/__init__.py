"""Job discovery & matching (Phase 5)."""

from job_hunt_assistant.discovery.match import (
    JobMatch,
    JobPosting,
    match_job,
    rank_jobs,
)
from job_hunt_assistant.discovery.source import JobSource, ManualJobSource
from job_hunt_assistant.discovery.web import WebJobSource

__all__ = [
    "JobPosting",
    "JobMatch",
    "match_job",
    "rank_jobs",
    "JobSource",
    "ManualJobSource",
    "WebJobSource",
]
