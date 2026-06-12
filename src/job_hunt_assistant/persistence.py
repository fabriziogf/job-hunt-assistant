"""Persistence — save and load the state a job hunt accumulates.

Every model in this project is JSON-able Pydantic, so persistence is a thin,
dependency-free layer: atomic JSON writes plus a ``Workspace`` that organizes the
durable artifacts (the pipeline, interview logs, saved application packages, and
cached company research) under one directory.

Atomic writes (write to a temp file, then ``os.replace``) mean a crash mid-write
never leaves a half-written, unloadable file — important for the pipeline, which
is updated repeatedly over weeks.
"""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from job_hunt_assistant.interview.log import InterviewLog
from job_hunt_assistant.orchestration import ApplicationPackage
from job_hunt_assistant.pipeline import Application, Pipeline
from job_hunt_assistant.profile import CandidateProfile
from job_hunt_assistant.research.company import CompanyResearch, ResearchProvider

T = TypeVar("T", bound=BaseModel)


def slugify(text: str) -> str:
    """A filesystem-safe slug, e.g. 'Northwind Commerce' -> 'northwind-commerce'."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "untitled"


def save_model(model: BaseModel, path: str | Path) -> Path:
    """Write a Pydantic model to JSON atomically, creating parent dirs."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to a temp file in the same directory, then atomically replace.
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(model.model_dump_json(indent=2))
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


def load_model(model_cls: type[T], path: str | Path) -> T:
    """Load and validate a Pydantic model from a JSON file."""
    return model_cls.model_validate_json(Path(path).read_text())


class Workspace:
    """A directory holding the durable state of one job hunt.

    Layout::

        <root>/
          profile.json
          pipeline.json
          logs/<company>-<date>.json
          packages/<company>-<role>.json
          research/<company>.json
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    # --- paths ---------------------------------------------------------------

    @property
    def profile_path(self) -> Path:
        return self.root / "profile.json"

    @property
    def pipeline_path(self) -> Path:
        return self.root / "pipeline.json"

    @property
    def logs_dir(self) -> Path:
        return self.root / "logs"

    @property
    def packages_dir(self) -> Path:
        return self.root / "packages"

    @property
    def research_dir(self) -> Path:
        return self.root / "research"

    # --- profile -------------------------------------------------------------

    def save_profile(self, profile: CandidateProfile) -> Path:
        return save_model(profile, self.profile_path)

    def load_profile(self) -> CandidateProfile | None:
        if not self.profile_path.exists():
            return None
        return load_model(CandidateProfile, self.profile_path)

    # --- pipeline ------------------------------------------------------------

    def load_pipeline(self) -> Pipeline:
        """The tracked applications (an empty pipeline if none saved yet)."""
        if not self.pipeline_path.exists():
            return Pipeline()
        return load_model(Pipeline, self.pipeline_path)

    def save_pipeline(self, pipeline: Pipeline) -> Path:
        return save_model(pipeline, self.pipeline_path)

    def track(self, application: Application) -> Pipeline:
        """Append an application to the saved pipeline and persist it."""
        pipeline = self.load_pipeline()
        pipeline.add(application)
        self.save_pipeline(pipeline)
        return pipeline

    # --- interview logs ------------------------------------------------------

    def save_interview_log(self, log: InterviewLog) -> Path:
        date_part = log.interview_date.isoformat() if log.interview_date else "undated"
        name = f"{slugify(log.company)}-{date_part}.json"
        return save_model(log, self.logs_dir / name)

    def load_interview_logs(self) -> list[InterviewLog]:
        if not self.logs_dir.exists():
            return []
        return [load_model(InterviewLog, p) for p in sorted(self.logs_dir.glob("*.json"))]

    # --- application packages ------------------------------------------------

    def save_package(self, package: ApplicationPackage, name: str | None = None) -> Path:
        slug = name or f"{slugify(package.job.company)}-{slugify(package.job.role)}"
        return save_model(package, self.packages_dir / f"{slug}.json")

    def load_packages(self) -> list[ApplicationPackage]:
        if not self.packages_dir.exists():
            return []
        return [
            load_model(ApplicationPackage, p)
            for p in sorted(self.packages_dir.glob("*.json"))
        ]

    # --- research cache ------------------------------------------------------

    def cache_research(self, research: CompanyResearch) -> Path:
        return save_model(research, self.research_dir / f"{slugify(research.company)}.json")

    def get_research(self, company: str) -> CompanyResearch | None:
        path = self.research_dir / f"{slugify(company)}.json"
        if not path.exists():
            return None
        return load_model(CompanyResearch, path)


class CachedResearchProvider:
    """Wraps any ``ResearchProvider`` with a disk cache in a ``Workspace``.

    A cache hit avoids a (potentially live, billable) lookup; a miss delegates to
    the wrapped provider and caches the result. Lets the expensive
    ``WebResearchProvider`` be reused across runs for the same company.
    """

    def __init__(self, provider: ResearchProvider, workspace: Workspace) -> None:
        self._provider = provider
        self._workspace = workspace

    def research(self, company: str) -> CompanyResearch:
        cached = self._workspace.get_research(company)
        if cached is not None:
            return cached
        research = self._provider.research(company)
        self._workspace.cache_research(research)
        return research
