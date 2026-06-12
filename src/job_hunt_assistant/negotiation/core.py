"""Offer Negotiation Advisor — deterministic core (Chapter 8).

Chapter 8: always negotiate (politely there's no risk); your maximum leverage is
the single moment of the offer. Know four numbers — market range, ranges by
component, your walk-away (never reveal), and your ask (10-20% above the offer).
This module turns an offer into a concrete plan: the ask range, the multi-lever
asks beyond base, the deflection scripts, the get-it-in-writing checklist, and
the compounding "cost of silence" that motivates asking at all.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# Chapter 8: the standard ask is 10-20% above the offer.
ASK_LOW_MULTIPLIER = 1.10
ASK_HIGH_MULTIPLIER = 1.20

# Levers to ask for beyond base salary (Chapter 8).
COMPENSATION_LEVERS: list[str] = [
    "Sign-on bonus",
    "Equity / stock refresh",
    "Extra (informal) vacation days",
    "Remote / flexible work arrangement",
    "Earlier review for the next raise",
    "Relocation assistance",
]

# Deflecting "what are your salary expectations?" (Chapter 8: let them go first).
DEFLECTION_SCRIPTS: list[str] = [
    "What's the budget for this role?",
    "I'd love to hear what you've allocated.",
    "I'm flexible — what's the range?",
]

# Get-it-in-writing checklist (Chapter 8).
GET_IT_IN_WRITING: list[str] = [
    "Verbal offers are not offers — wait for the written letter.",
    "Get any promises they made written into the offer letter.",
    "Keep interviewing elsewhere until you've signed.",
    "Once signed, anything not in writing doesn't exist.",
]


def ask_range(offer_base: float) -> tuple[float, float]:
    """The Chapter 8 ask band: 10-20% above the offered base."""
    return (
        round(offer_base * ASK_LOW_MULTIPLIER, 2),
        round(offer_base * ASK_HIGH_MULTIPLIER, 2),
    )


def lifetime_value_of_raise(
    raise_amount: float,
    *,
    years: int = 40,
    annual_raise: float = 0.03,
    return_rate: float = 0.05,
) -> float:
    """The compounding "cost of silence" (Chapter 8).

    A raise won today compounds: it grows with standard annual raises and, banked
    each year, earns an investment return until retirement. With the defaults, a
    $5,000 raise at 25 is worth ~$1M by retirement — the chapter's headline.
    """
    total = 0.0
    for t in range(years):
        years_salary = raise_amount * (1 + annual_raise) ** t
        total += years_salary * (1 + return_rate) ** (years - t - 1)
    return round(total, 2)


class NegotiationPlan(BaseModel):
    """A concrete, polite negotiation plan built from an offer."""

    offer_base: float
    ask_low: float
    ask_high: float
    walk_away: float | None = None
    market_low: float | None = None
    market_high: float | None = None
    levers: list[str] = Field(default_factory=lambda: list(COMPENSATION_LEVERS))
    deflection_scripts: list[str] = Field(
        default_factory=lambda: list(DEFLECTION_SCRIPTS)
    )
    notes: list[str] = Field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "## Negotiation plan",
            f"- Offer base: {self.offer_base:,.0f}",
            f"- Ask range (10-20% above): {self.ask_low:,.0f}-{self.ask_high:,.0f}",
        ]
        if self.market_low is not None and self.market_high is not None:
            lines.append(f"- Market range: {self.market_low:,.0f}-{self.market_high:,.0f}")
        if self.walk_away is not None:
            lines.append(f"- Walk-away (never reveal): {self.walk_away:,.0f}")
        if self.notes:
            lines.append("\n**Notes:**")
            lines += [f"- {n}" for n in self.notes]
        lines.append("\n**If they say no on base, ask for another lever:**")
        lines += [f"- {lever}" for lever in self.levers]
        return "\n".join(lines) + "\n"


def build_negotiation_plan(
    offer_base: float,
    *,
    market_low: float | None = None,
    market_high: float | None = None,
    walk_away: float | None = None,
) -> NegotiationPlan:
    """Build a negotiation plan from an offer and optional market/walk-away data."""
    low, high = ask_range(offer_base)
    notes: list[str] = ["Always ask — politely, there's no risk. Don't seem greedy."]

    if market_low is not None and offer_base < market_low:
        notes.append(
            f"The offer ({offer_base:,.0f}) is below the market floor "
            f"({market_low:,.0f}) — you have a strong, data-backed case."
        )
    if market_high is not None and market_high > high:
        notes.append(
            f"Market goes to {market_high:,.0f}; you can push above the 20% ask "
            "if the data supports it."
        )
    if walk_away is not None and walk_away > offer_base:
        notes.append(
            "Your walk-away is above the current offer — be ready to decline if "
            "they can't move. Never reveal the number."
        )

    return NegotiationPlan(
        offer_base=offer_base,
        ask_low=low,
        ask_high=high,
        walk_away=walk_away,
        market_low=market_low,
        market_high=market_high,
        notes=notes,
    )
