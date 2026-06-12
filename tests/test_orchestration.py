"""Tests for the end-to-end orchestrator (Phase 5).

The orchestrator runs fully offline by default; injected LLM components are
exercised with fakes — no API key.
"""

from datetime import date

from job_hunt_assistant import (
    ApplicationOrchestrator,
    CompanyFact,
    CompanyResearch,
    JobPosting,
    ManualResearchProvider,
    load_sample_profile,
)
from job_hunt_assistant.coverletter.models import CoverLetter
from job_hunt_assistant.interview.questions import QuestionBank
from job_hunt_assistant.pipeline import ApplicationStatus

AS_OF = date(2026, 6, 11)


def _job() -> JobPosting:
    return JobPosting(
        company="Northwind Commerce",
        role="Senior Product Manager",
        description="Own recommender systems and LLM personalization across web "
        "and mobile; run A/B experiments and apply causal inference.",
    )


# --- Deterministic default (no LLM injected) ---------------------------------


def test_prepare_runs_fully_offline_by_default():
    orch = ApplicationOrchestrator(load_sample_profile(), as_of=AS_OF)
    pkg = orch.prepare(_job())

    # Resume + ATS produced deterministically.
    assert pkg.resume.experiences
    assert 0 <= pkg.ats.score <= 100
    # No writer injected -> no cover letter, canonical question bank.
    assert pkg.cover_letter is None
    assert pkg.question_bank.count == 12  # the canonical 12


def test_to_application_hands_off_to_pipeline():
    orch = ApplicationOrchestrator(load_sample_profile(), as_of=AS_OF)
    job = _job()
    app = orch.to_application(job)
    assert app.company == "Northwind Commerce"
    assert app.date_applied == AS_OF
    assert app.status is ApplicationStatus.APPLIED


# --- With injected LLM components (fakes) ------------------------------------


class _FakeResponse:
    def __init__(self, parsed):
        self.parsed_output = parsed


class _FakeMessages:
    def __init__(self, parsed):
        self._parsed = parsed
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._parsed)


class _FakeClient:
    def __init__(self, parsed):
        self.messages = _FakeMessages(parsed)


def test_prepare_uses_injected_cover_letter_writer_and_research():
    from job_hunt_assistant.coverletter.writer import CoverLetterWriter

    drafted = CoverLetter(
        salutation="Dear Ms. Chen,", paragraphs=["a", "b", "c", "d"], signoff="Best,"
    )
    writer = CoverLetterWriter(client=_FakeClient(drafted))
    provider = ManualResearchProvider(
        [
            CompanyResearch(
                company="Northwind Commerce",
                hiring_manager_name="Dana Chen",
                facts=[CompanyFact(text="launched same-day delivery")],
            )
        ]
    )
    orch = ApplicationOrchestrator(
        load_sample_profile(),
        cover_letter_writer=writer,
        research_provider=provider,
        as_of=AS_OF,
    )
    pkg = orch.prepare(_job())

    assert pkg.cover_letter is not None
    # The research the provider resolved was passed into the writer's prompt.
    user_msg = writer._client.messages.calls[0]["messages"][0]["content"]
    assert "same-day delivery" in user_msg
    assert "Dana Chen" in user_msg


def test_prepare_uses_injected_question_generator():
    from job_hunt_assistant.interview.generator import (
        GeneratedQuestions,
        QuestionGenerator,
    )
    from job_hunt_assistant.interview.questions import (
        InterviewQuestion,
        QuestionCategory,
    )

    extra = GeneratedQuestions(
        questions=[
            InterviewQuestion(text=f"Q{i}", category=QuestionCategory.ROLE_SPECIFIC)
            for i in range(18)
        ]
    )
    gen = QuestionGenerator(client=_FakeClient(extra))
    orch = ApplicationOrchestrator(
        load_sample_profile(), question_generator=gen, as_of=AS_OF
    )
    pkg = orch.prepare(_job())
    assert isinstance(pkg.question_bank, QuestionBank)
    assert pkg.question_bank.count == 30  # canonical 12 + 18 generated


def test_missing_research_does_not_crash():
    from job_hunt_assistant.coverletter.writer import CoverLetterWriter

    writer = CoverLetterWriter(
        client=_FakeClient(
            CoverLetter(salutation="Hi,", paragraphs=["a", "b", "c", "d"], signoff="x")
        )
    )
    # Provider has no entry for this company -> orchestrator falls back to None.
    orch = ApplicationOrchestrator(
        load_sample_profile(),
        cover_letter_writer=writer,
        research_provider=ManualResearchProvider([]),
        as_of=AS_OF,
    )
    pkg = orch.prepare(_job())
    assert pkg.cover_letter is not None  # still drafts, just without research
