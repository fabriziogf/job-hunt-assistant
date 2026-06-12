"""LLM-backed X/Y/Z bullet rewriter (Chapter 2).

This is the judgement half of the Resume Builder — it rewrites a verified
achievement into a polished "Accomplished [X] as measured by [Y] by doing [Z]"
bullet, optionally tailored to a target job description.

Design notes:
- **Honesty is the hard constraint.** The system prompt forbids inventing
  metrics, employers, or outcomes. If the source achievement has no measurable
  result, the model must keep the bullet qualitative rather than fabricate a
  number — and report that via ``has_metric=False``. This enforces the project's
  "never fabricate" rule at the prompt level, on top of the ``verified`` gate.
- **Prompt construction is separated from the API call** (`build_rewrite_prompt`
  is a pure function), so the grounding logic is unit-tested without a key.
- **The Anthropic client is injected**, so tests pass a fake and never hit the
  network. Real use resolves credentials from ``ANTHROPIC_API_KEY``.

Grounding comes from the playbook loader (`PLAYBOOK.as_prompt`), so the rules the
model follows are the same Chapter 1–2 principles documented elsewhere.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from job_hunt_assistant.playbook import PLAYBOOK, AgentSkill
from job_hunt_assistant.profile import Achievement

MODEL = "claude-opus-4-8"
MAX_TOKENS = 1024

_HONESTY_RULES = """\
You rewrite a single resume bullet. Absolute rules, in priority order:
1. NEVER invent facts. Use only the information in the provided achievement.
   Do not add numbers, percentages, dollar amounts, time spans, employer names,
   technologies, or outcomes that are not already present.
2. If the achievement has no measurable result (no Y), DO NOT fabricate one.
   Write the strongest truthful bullet you can without a metric, and set
   has_metric to false so a human knows to supply a real number.
3. Follow the X/Y/Z formula: lead with a strong past-tense action verb, state
   the result, and include how it was done when that detail is present.
4. One sentence. No first-person pronouns. No period-padding or filler.
If a target job description is provided, mirror its phrasing ONLY where it
truthfully matches the achievement — never to imply experience the candidate
lacks."""


class BulletRewrite(BaseModel):
    """Structured result of rewriting one achievement."""

    rewritten: str = Field(..., description="The rewritten one-line bullet.")
    has_metric: bool = Field(
        ...,
        description="True if the bullet contains a real measurable result (Y) "
        "drawn from the source — never fabricated.",
    )
    notes: str = Field(
        "", description="Optional note, e.g. what metric the human should add."
    )


def build_rewrite_prompt(
    achievement: Achievement, job_description: str | None = None
) -> tuple[str, str]:
    """Build the (system, user) prompt for rewriting one achievement.

    Pure function — no API call — so the grounding can be tested directly.
    """
    system = "\n\n".join(
        [PLAYBOOK.as_prompt(AgentSkill.RESUME_BUILDER), _HONESTY_RULES]
    )

    lines = ["Rewrite this achievement into one X/Y/Z bullet.", "", "ACHIEVEMENT:"]
    lines.append(f"- What (X): {achievement.what}")
    lines.append(
        f"- Measured by (Y): {achievement.measured_by}"
        if achievement.measured_by
        else "- Measured by (Y): (none provided — do not invent one)"
    )
    lines.append(
        f"- How (Z): {achievement.how}"
        if achievement.how
        else "- How (Z): (none provided)"
    )
    if job_description:
        lines += [
            "",
            "TARGET JOB DESCRIPTION (mirror phrasing only where truthful):",
            job_description.strip(),
        ]
    return system, "\n".join(lines)


class SupportsParse(Protocol):
    """The slice of the Anthropic client this module needs (for injection)."""

    @property
    def messages(self) -> object: ...


class ResumeRewriter:
    """Rewrites verified achievements into X/Y/Z bullets via Claude.

    Pass a client for testing; in production it lazily constructs the default
    ``anthropic.Anthropic()``, which reads ``ANTHROPIC_API_KEY`` from the env.
    """

    def __init__(self, client: SupportsParse | None = None) -> None:
        self._client = client

    def _get_client(self) -> SupportsParse:
        if self._client is None:
            import anthropic  # imported lazily so tests need no key

            self._client = anthropic.Anthropic()
        return self._client

    def rewrite(
        self, achievement: Achievement, job_description: str | None = None
    ) -> BulletRewrite:
        """Rewrite one achievement. Only verified achievements should be passed."""
        if not achievement.verified:
            raise ValueError(
                "Refusing to rewrite an unverified achievement — verify it first "
                "(the agent never fabricates or polishes unconfirmed claims)."
            )
        system, user = build_rewrite_prompt(achievement, job_description)
        response = self._get_client().messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=BulletRewrite,
        )
        return response.parsed_output

    def rewrite_verified(
        self, achievements: list[Achievement], job_description: str | None = None
    ) -> list[BulletRewrite]:
        """Rewrite every verified achievement in a list; skip unverified ones."""
        return [
            self.rewrite(a, job_description) for a in achievements if a.verified
        ]
