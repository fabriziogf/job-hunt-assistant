"""Offer Negotiation Advisor skill (Phase 4, Chapter 8)."""

from job_hunt_assistant.negotiation.core import (
    COMPENSATION_LEVERS,
    DEFLECTION_SCRIPTS,
    GET_IT_IN_WRITING,
    NegotiationPlan,
    ask_range,
    build_negotiation_plan,
    lifetime_value_of_raise,
)
from job_hunt_assistant.negotiation.writer import (
    CounterOffer,
    CounterOfferWriter,
    build_counter_offer_prompt,
)

__all__ = [
    "NegotiationPlan",
    "build_negotiation_plan",
    "ask_range",
    "lifetime_value_of_raise",
    "COMPENSATION_LEVERS",
    "DEFLECTION_SCRIPTS",
    "GET_IT_IN_WRITING",
    "CounterOffer",
    "CounterOfferWriter",
    "build_counter_offer_prompt",
]
