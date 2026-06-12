"""Job sources — where postings come from.

Mirrors the company-research design: a ``JobSource`` interface with a manual
implementation (you supply postings) so everything stays offline and testable,
and a live web-backed implementation (``discovery/web.py``) that fills the same
shape from a real search. The matcher and orchestrator depend on the interface,
not the source.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from job_hunt_assistant.discovery.match import JobPosting


@runtime_checkable
class JobSource(Protocol):
    """How postings are obtained. Swap implementations freely."""

    def search(
        self, query: str, *, location: str | None = None, limit: int = 10
    ) -> list[JobPosting]: ...


class ManualJobSource:
    """Postings supplied by hand — the offline default.

    ``search`` does a simple case-insensitive keyword filter over the stored
    postings (company, role, description), so it behaves like a tiny local board.
    """

    def __init__(self, postings: list[JobPosting] | None = None) -> None:
        self._postings = list(postings or [])

    def add(self, posting: JobPosting) -> None:
        self._postings.append(posting)

    def search(
        self, query: str, *, location: str | None = None, limit: int = 10
    ) -> list[JobPosting]:
        terms = [t for t in query.lower().split() if t]
        results = []
        for p in self._postings:
            hay = f"{p.company} {p.role} {p.description}".lower()
            if all(t in hay for t in terms):
                if location and location.lower() not in (p.location or "").lower():
                    continue
                results.append(p)
        return results[:limit]
