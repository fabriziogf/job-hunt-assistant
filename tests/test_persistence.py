"""Tests for the persistence layer."""

from datetime import date

from job_hunt_assistant import (
    CachedResearchProvider,
    CompanyResearch,
    Workspace,
    load_model,
    save_model,
    slugify,
)
from job_hunt_assistant.interview.log import AnsweredQuestion, InterviewLog
from job_hunt_assistant.pipeline import Application, ApplicationStatus, Pipeline


# --- generic helpers ---------------------------------------------------------


def test_save_load_round_trip(tmp_path):
    pipe = Pipeline(
        applications=[
            Application(company="Acme", role="PM", date_applied=date(2026, 5, 1))
        ]
    )
    path = save_model(pipe, tmp_path / "pipeline.json")
    assert path.exists()
    restored = load_model(Pipeline, path)
    assert restored == pipe


def test_save_is_atomic_no_tmp_left_behind(tmp_path):
    save_model(Pipeline(), tmp_path / "p.json")
    leftovers = list(tmp_path.glob("*.tmp"))
    assert leftovers == []


def test_slugify():
    assert slugify("Northwind Commerce") == "northwind-commerce"
    assert slugify("  A/B  Co! ") == "a-b-co"
    assert slugify("") == "untitled"


# --- Workspace: pipeline -----------------------------------------------------


def test_track_persists_across_instances(tmp_path):
    ws = Workspace(tmp_path)
    assert ws.load_pipeline().applications == []  # empty by default

    ws.track(Application(company="Acme", role="PM", date_applied=date(2026, 5, 1)))
    ws.track(Application(company="Globex", role="PM", date_applied=date(2026, 5, 2)))

    # A fresh Workspace over the same dir sees the saved state.
    reopened = Workspace(tmp_path)
    pipe = reopened.load_pipeline()
    assert [a.company for a in pipe.applications] == ["Acme", "Globex"]


# --- Workspace: interview logs ----------------------------------------------


def test_interview_logs_save_and_load(tmp_path):
    ws = Workspace(tmp_path)
    ws.save_interview_log(
        InterviewLog(
            company="Acme",
            interview_date=date(2026, 6, 1),
            answered=[AnsweredQuestion(question="Tell me about yourself.", score=8)],
        )
    )
    logs = ws.load_interview_logs()
    assert len(logs) == 1
    assert logs[0].company == "Acme"
    assert (ws.logs_dir / "acme-2026-06-01.json").exists()


# --- Workspace: research cache ----------------------------------------------


def test_research_cache(tmp_path):
    ws = Workspace(tmp_path)
    assert ws.get_research("Northwind") is None
    ws.cache_research(CompanyResearch(company="Northwind"))
    assert ws.get_research("northwind") is not None  # case-insensitive slug


class _CountingProvider:
    """Counts how many times the underlying (expensive) lookup runs."""

    def __init__(self):
        self.calls = 0

    def research(self, company: str) -> CompanyResearch:
        self.calls += 1
        return CompanyResearch(company=company)


def test_cached_provider_only_calls_through_on_miss(tmp_path):
    inner = _CountingProvider()
    cached = CachedResearchProvider(inner, Workspace(tmp_path))

    cached.research("Acme")  # miss -> delegates + caches
    cached.research("Acme")  # hit -> no delegation
    assert inner.calls == 1
