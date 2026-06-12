"""Job discovery & matching (Phase 5)."""

from job_hunt_assistant.discovery.match import (
    JobMatch,
    JobPosting,
    match_job,
    rank_jobs,
)

__all__ = [
    "JobPosting",
    "JobMatch",
    "match_job",
    "rank_jobs",
]
