"""Orchestration — tie the seven skills into one end-to-end flow (Phase 5).

The ``ApplicationOrchestrator`` holds the candidate profile and turns a single
``JobPosting`` into a complete ``ApplicationPackage``: a tailored resume, its ATS
score against the posting, a cover letter, and an interview question bank — then
hands off to the pipeline tracker.

Design: the orchestrator composes the **deterministic** halves of each skill by
default, and accepts **injected** LLM components (resume rewriter, cover-letter
writer, question generator) for the generative steps. With nothing injected it
runs fully offline and still produces a usable package; inject the writers and it
upgrades each piece to model quality. Company research is resolved through the
same ``ResearchProvider`` seam from Phase 2.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from job_hunt_assistant.ats import ATSReport, score_resume
from job_hunt_assistant.coverletter.models import CoverLetter, LetterFormat
from job_hunt_assistant.coverletter.writer import CoverLetterWriter
from job_hunt_assistant.discovery.match import JobPosting
from job_hunt_assistant.interview.generator import QuestionGenerator
from job_hunt_assistant.interview.questions import QuestionBank
from job_hunt_assistant.pipeline.core import Application
from job_hunt_assistant.profile import CandidateProfile
from job_hunt_assistant.research.company import CompanyResearch, ResearchProvider
from job_hunt_assistant.resume import Resume, ResumeRewriter, build_resume


class ApplicationPackage(BaseModel):
    """Everything produced for one application, in one structured object."""

    job: JobPosting
    resume: Resume
    ats: ATSReport
    question_bank: QuestionBank
    cover_letter: CoverLetter | None = None


class ApplicationOrchestrator:
    """Runs the skills in order for one candidate across many jobs."""

    def __init__(
        self,
        profile: CandidateProfile,
        *,
        rewriter: ResumeRewriter | None = None,
        cover_letter_writer: CoverLetterWriter | None = None,
        question_generator: QuestionGenerator | None = None,
        research_provider: ResearchProvider | None = None,
        as_of: date | None = None,
    ) -> None:
        self.profile = profile
        self.rewriter = rewriter
        self.cover_letter_writer = cover_letter_writer
        self.question_generator = question_generator
        self.research_provider = research_provider
        self.as_of = as_of

    def _resolve_research(
        self, job: JobPosting, research: CompanyResearch | None
    ) -> CompanyResearch | None:
        if research is not None:
            return research
        if self.research_provider is None:
            return None
        try:
            return self.research_provider.research(job.company)
        except KeyError:
            return None  # no research for this company; cover letter stays general

    def prepare(
        self,
        job: JobPosting,
        *,
        research: CompanyResearch | None = None,
        fmt: LetterFormat = LetterFormat.LETTER,
    ) -> ApplicationPackage:
        """Build the full application package for one job."""
        # Phase 1 — tailored resume + ATS score.
        resume = build_resume(
            self.profile,
            job_description=job.description,
            rewriter=self.rewriter,
            as_of=self.as_of,
        )
        ats = score_resume(resume, job.description)

        # Phase 2 — cover letter (only if a writer is injected).
        cover_letter: CoverLetter | None = None
        if self.cover_letter_writer is not None:
            resolved = self._resolve_research(job, research)
            cover_letter = self.cover_letter_writer.write(
                self.profile,
                company=job.company,
                role=job.role,
                job_description=job.description,
                research=resolved,
                fmt=fmt,
            )

        # Phase 3 — interview question bank (canonical 12 by default).
        if self.question_generator is not None:
            question_bank = self.question_generator.generate(
                role=job.role, company=job.company, job_description=job.description
            )
        else:
            question_bank = QuestionBank.with_canonical()

        return ApplicationPackage(
            job=job,
            resume=resume,
            ats=ats,
            question_bank=question_bank,
            cover_letter=cover_letter,
        )

    def to_application(self, job: JobPosting) -> Application:
        """A pipeline-tracker record for this job (Phase 4 hand-off)."""
        return Application(
            company=job.company,
            role=job.role,
            date_applied=self.as_of or date.today(),
            tier=job.tier,
        )
