"""LLM generators for interview prep (Chapters 5 & 6).

Two model-backed pieces, both following the project's testable pattern (pure
prompt builder + injected Anthropic client):

- ``QuestionGenerator`` expands the canonical 12 toward ~30 by adding
  role/company-specific questions.
- ``AnswerCoach`` drafts the two four-part answers per question, with stories
  drawn ONLY from the candidate's verified achievements (never fabricated).
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from job_hunt_assistant.interview.answers import Answer, AnswerSet
from job_hunt_assistant.interview.questions import (
    TARGET_QUESTION_COUNT,
    InterviewQuestion,
    QuestionBank,
    QuestionCategory,
    canonical_questions,
)
from job_hunt_assistant.playbook import PLAYBOOK, AgentSkill
from job_hunt_assistant.profile import CandidateProfile

MODEL = "claude-opus-4-8"
MAX_TOKENS = 2000


class SupportsParse(Protocol):
    @property
    def messages(self) -> object: ...


# --- Question generation -----------------------------------------------------


class GeneratedQuestions(BaseModel):
    questions: list[InterviewQuestion] = Field(default_factory=list)


def build_question_prompt(
    *,
    role: str,
    company: str,
    job_description: str | None = None,
    needed: int,
) -> tuple[str, str]:
    """Pure prompt for generating role-specific questions."""
    system = "\n\n".join(
        [
            PLAYBOOK.as_prompt(AgentSkill.INTERVIEW_PREP),
            "Generate likely interview questions tailored to a specific role. "
            "Focus on role_specific and behavioral questions an interviewer for "
            "THIS job would actually ask. Do not repeat the standard questions "
            "(tell me about yourself, why this company, strengths/weaknesses, "
            "etc.) — those are already covered.",
        ]
    )
    parts = [
        f"Generate {needed} additional interview questions for a {role} at "
        f"{company}.",
        "Tag each with the best category.",
    ]
    if job_description:
        parts += ["", "JOB DESCRIPTION:", job_description.strip()]
    return system, "\n".join(parts)


class QuestionGenerator:
    """Expands the canonical question set with role-specific questions."""

    def __init__(self, client: SupportsParse | None = None) -> None:
        self._client = client

    def _get_client(self) -> SupportsParse:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def generate(
        self,
        *,
        role: str,
        company: str,
        job_description: str | None = None,
        target: int = TARGET_QUESTION_COUNT,
    ) -> QuestionBank:
        """Return a bank of ~target questions: the canonical 12 plus tailored ones."""
        bank = QuestionBank.with_canonical()
        needed = max(0, target - bank.count)
        if needed == 0:
            return bank
        system, user = build_question_prompt(
            role=role, company=company, job_description=job_description, needed=needed
        )
        response = self._get_client().messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=GeneratedQuestions,
        )
        for q in response.parsed_output.questions:
            # Generated questions are role-specific by construction.
            if q.category is QuestionCategory.ROLE_SPECIFIC or not q.canonical:
                q.canonical = False
            bank.add(q)
        return bank


# --- Answer coaching ---------------------------------------------------------

_ANSWER_HONESTY_RULES = """\
Hard rules:
1. Every story must be REAL — draw only on the candidate's verified achievements
   provided below. Never invent metrics, employers, projects, or outcomes.
2. Set achievement_tag to identify which achievement each story draws on.
3. Follow the four-part structure exactly: restate the question, preview your
   point, tell the specific story (with numbers when the achievement has them),
   then summarize. Keep each answer tight enough to say aloud in under a minute.
4. Produce TWO genuinely different answers (different stories or angles), so a
   second interviewer who repeats the question gets a fresh one.
For non-behavioral questions (motivation, weakness), stay truthful: base answers
on the real profile, not invented enthusiasm or fake flaws."""


def build_answer_prompt(
    question: str,
    profile: CandidateProfile,
    *,
    company: str | None = None,
    role: str | None = None,
) -> tuple[str, str]:
    """Pure prompt for drafting two four-part answers to one question."""
    system = "\n\n".join(
        [PLAYBOOK.as_prompt(AgentSkill.INTERVIEW_PREP), _ANSWER_HONESTY_RULES]
    )
    lines = [f"Draft two answers to this interview question:", f'"{question}"']
    if role or company:
        target = " at ".join(p for p in [role, company] if p)
        lines.append(f"Context: interviewing for {target}.")
    lines += ["", "CANDIDATE VERIFIED ACHIEVEMENTS (the only allowed story material):"]
    verified = profile.verified_achievements()
    if verified:
        for a in verified:
            lines.append(f"- {a.to_xyz_bullet()}")
    else:
        lines.append("- (none verified yet — keep answers truthful and general)")
    return system, "\n".join(lines)


class AnswerCoach:
    """Drafts the two four-part answers per question, from verified stories."""

    def __init__(self, client: SupportsParse | None = None) -> None:
        self._client = client

    def _get_client(self) -> SupportsParse:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def generate(
        self,
        question: str,
        profile: CandidateProfile,
        *,
        company: str | None = None,
        role: str | None = None,
    ) -> AnswerSet:
        system, user = build_answer_prompt(
            question, profile, company=company, role=role
        )
        response = self._get_client().messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=AnswerSet,
        )
        result = response.parsed_output
        result.question = question  # ensure the question is recorded
        return result
