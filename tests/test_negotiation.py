"""Tests for the Offer Negotiation Advisor (Chapter 8)."""

from job_hunt_assistant.negotiation import (
    COMPENSATION_LEVERS,
    DEFLECTION_SCRIPTS,
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


# --- Deterministic math ------------------------------------------------------


def test_ask_range_is_10_to_20_percent_above():
    low, high = ask_range(100_000)
    assert low == 110_000
    assert high == 120_000


def test_lifetime_value_matches_playbook_million():
    # $5k raise compounds to ~$1M over a career (Chapter 8 headline).
    value = lifetime_value_of_raise(5_000)
    assert 800_000 < value < 1_200_000
    # And it scales with the raise.
    assert lifetime_value_of_raise(10_000) > value


def test_levers_and_scripts_present():
    assert any("Sign-on" in l for l in COMPENSATION_LEVERS)
    assert any("range" in s.lower() for s in DEFLECTION_SCRIPTS)


# --- Plan builder ------------------------------------------------------------


def test_plan_sets_ask_and_default_levers():
    plan = build_negotiation_plan(150_000)
    assert plan.ask_low == 165_000
    assert plan.ask_high == 180_000
    assert plan.levers  # defaults to the standard levers
    assert any("greedy" in n.lower() for n in plan.notes)


def test_plan_flags_below_market_offer():
    plan = build_negotiation_plan(120_000, market_low=140_000, market_high=170_000)
    notes = " ".join(plan.notes).lower()
    assert "below the market floor" in notes
    assert "push above the 20%" in notes


def test_plan_markdown_renders_ask_and_levers():
    md = build_negotiation_plan(150_000, walk_away=160_000).to_markdown()
    assert "Negotiation plan" in md
    assert "Ask range" in md
    assert "Sign-on bonus" in md
    assert "never reveal" in md.lower()


# --- LLM counter-offer writer (fake client) ----------------------------------


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


def test_counter_offer_prompt_grounds_and_forbids_lying():
    plan = build_negotiation_plan(150_000)
    system, user = build_counter_offer_prompt(
        plan, justification="market data from Levels.fyi", your_name="Jordan"
    )
    assert "Chapter 8" in system
    assert "NEVER lie" in system
    assert "market data from Levels.fyi" in user


def test_counter_offer_writer_calls_model_with_schema():
    client = _FakeClient(CounterOffer(body="Thank you for the offer..."))
    writer = CounterOfferWriter(client=client)
    plan = build_negotiation_plan(150_000)
    writer.write(plan, justification="competing offer", your_name="Jordan")
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert call["output_format"] is CounterOffer
