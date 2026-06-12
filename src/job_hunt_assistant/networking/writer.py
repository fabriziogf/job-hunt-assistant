"""LLM outreach writer (Chapter 4).

Drafts a short "ask for advice, not a job" message to a contact, opening with a
genuine coincidence the candidate supplies. Honesty: the model may use only the
provided coincidence/mutual-connection — it must not invent a shared detail.

Same testable shape as the other writers: pure prompt builder + injected client.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from job_hunt_assistant.networking.core import OutreachContact
from job_hunt_assistant.playbook import PLAYBOOK, AgentSkill

MODEL = "claude-opus-4-8"
MAX_TOKENS = 800

_RULES = """\
Hard rules:
1. Ask for ADVICE, not a job. Never ask to be hired, referred, or considered for
   a role in this first message.
2. Open with the EXACT coincidence provided — do not invent a shared detail. If
   none is provided, keep the opener honest and general.
3. Keep it short (a few sentences) — you're asking for a 15-minute call.
4. Warm, specific, low-pressure. End with a no-obligation thank-you."""


class OutreachMessage(BaseModel):
    subject: str | None = None
    body: str


def build_outreach_prompt(
    contact: OutreachContact,
    *,
    field: str,
    your_name: str,
    your_background: str | None = None,
) -> tuple[str, str]:
    """Pure prompt for drafting an advice-ask outreach message."""
    system = "\n\n".join([PLAYBOOK.as_prompt(AgentSkill.NETWORKING), _RULES])
    lines = [
        f"Write a short outreach message from {your_name} asking {contact.name} "
        f"for 15 minutes of advice about moving into {field}.",
    ]
    if contact.title or contact.company:
        who = " at ".join(p for p in [contact.title, contact.company] if p)
        lines.append(f"They are: {who}.")
    if contact.coincidence:
        lines.append(f"Genuine coincidence to open with: {contact.coincidence}")
    else:
        lines.append("No coincidence provided — keep the opener honest and general.")
    if contact.mutual_connection:
        lines.append(f"Mutual connection: {contact.mutual_connection}")
    if your_background:
        lines.append(f"Your background: {your_background}")
    return system, "\n".join(lines)


class SupportsParse(Protocol):
    @property
    def messages(self) -> object: ...


class OutreachWriter:
    """Drafts advice-ask outreach via Claude."""

    def __init__(self, client: SupportsParse | None = None) -> None:
        self._client = client

    def _get_client(self) -> SupportsParse:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def write(
        self,
        contact: OutreachContact,
        *,
        field: str,
        your_name: str,
        your_background: str | None = None,
    ) -> OutreachMessage:
        system, user = build_outreach_prompt(
            contact, field=field, your_name=your_name, your_background=your_background
        )
        response = self._get_client().messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=OutreachMessage,
        )
        return response.parsed_output
