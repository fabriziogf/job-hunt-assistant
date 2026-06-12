"""LLM counter-offer drafter (Chapter 8).

Drafts a polite, non-greedy counter-offer message grounded in a NegotiationPlan
and the candidate's real justifications. Chapter 8 is emphatic: never lie. The
prompt allows only the justifications the candidate actually provides (market
data, a real competing offer, genuine obligations) — it must not invent leverage.

Same testable shape: pure prompt builder + injected client.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from job_hunt_assistant.negotiation.core import NegotiationPlan
from job_hunt_assistant.playbook import PLAYBOOK, AgentSkill

MODEL = "claude-opus-4-8"
MAX_TOKENS = 900

_RULES = """\
Hard rules:
1. NEVER lie or invent leverage. Use only the justifications provided below
   (market data, a real competing offer, genuine personal obligations).
2. Be polite and appreciative — they already chose the candidate. Do not come
   across as greedy, demanding, or transactional.
3. Anchor on the ask number; if they can't move on base, invite other levers
   (sign-on, equity, vacation, remote, earlier review, relocation).
4. Keep it brief and warm. Ask, don't demand."""


class CounterOffer(BaseModel):
    subject: str | None = None
    body: str


def build_counter_offer_prompt(
    plan: NegotiationPlan,
    *,
    justification: str,
    your_name: str,
    role: str | None = None,
    company: str | None = None,
    competing_offer: str | None = None,
) -> tuple[str, str]:
    """Pure prompt for drafting a counter-offer message."""
    system = "\n\n".join([PLAYBOOK.as_prompt(AgentSkill.NEGOTIATION), _RULES])
    target = " at ".join(p for p in [role, company] if p)
    lines = [
        f"Draft a polite counter-offer message from {your_name}"
        + (f" for the {target} offer." if target else "."),
        f"Current base offer: {plan.offer_base:,.0f}",
        f"Ask: {plan.ask_low:,.0f}-{plan.ask_high:,.0f} (anchor near the top).",
        f"Justification (the ONLY allowed leverage): {justification}",
    ]
    if competing_offer:
        lines.append(f"Real competing offer: {competing_offer}")
    lines.append("Levers to offer if base can't move: " + ", ".join(plan.levers))
    return system, "\n".join(lines)


class SupportsParse(Protocol):
    @property
    def messages(self) -> object: ...


class CounterOfferWriter:
    """Drafts a counter-offer message via Claude."""

    def __init__(self, client: SupportsParse | None = None) -> None:
        self._client = client

    def _get_client(self) -> SupportsParse:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def write(
        self,
        plan: NegotiationPlan,
        *,
        justification: str,
        your_name: str,
        role: str | None = None,
        company: str | None = None,
        competing_offer: str | None = None,
    ) -> CounterOffer:
        system, user = build_counter_offer_prompt(
            plan,
            justification=justification,
            your_name=your_name,
            role=role,
            company=company,
            competing_offer=competing_offer,
        )
        response = self._get_client().messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=CounterOffer,
        )
        return response.parsed_output
