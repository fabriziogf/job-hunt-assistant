"""Tests for the Networking & Referral Assistant (Chapter 4)."""

from job_hunt_assistant.networking import (
    ADVICE_QUESTIONS,
    MEETING_ETIQUETTE,
    OutreachContact,
    lint_outreach,
    outreach_template,
)
from job_hunt_assistant.networking.writer import (
    OutreachMessage,
    OutreachWriter,
    build_outreach_prompt,
)


# --- Deterministic content ---------------------------------------------------


def test_five_advice_questions():
    assert len(ADVICE_QUESTIONS) == 5
    assert ADVICE_QUESTIONS[0] == "How did you get your job?"
    assert any("refer me to the recruiter" in q for q in ADVICE_QUESTIONS)


def test_outreach_template_fills_and_asks_for_advice():
    msg = outreach_template(
        name="Dana",
        coincidence="I saw your post on recommender systems.",
        field="AI product management",
        your_name="Jordan Rivera",
        your_contact="jordan@example.com",
    )
    assert "Hi Dana —" in msg
    assert "I saw your post" in msg
    assert "advice" in msg
    assert "15-minute call" in msg
    assert msg.strip().endswith("jordan@example.com")


def test_etiquette_covers_thank_you_and_ending_on_time():
    joined = " ".join(MEETING_ETIQUETTE).lower()
    assert "thank-you" in joined
    assert "end" in joined


# --- Outreach linter ---------------------------------------------------------


def test_lint_flags_asking_for_a_job():
    report = lint_outreach("Hi, I noticed your work. Are you hiring? I'd love a job.")
    assert report.by_code("asks_for_job")


def test_lint_flags_generic_opener_and_missing_coincidence():
    report = lint_outreach("You don't know me, but I want to talk to you.")
    assert report.by_code("generic_opener")
    assert report.by_code("no_coincidence")


def test_lint_clean_advice_message_passes_core_checks():
    good = (
        "Hi Dana — I saw your post on recommender systems. I'm exploring a move "
        "into AI product management and would love your advice on how you got "
        "started. Either way, thanks for the inspiration."
    )
    report = lint_outreach(good)
    assert not report.by_code("asks_for_job")
    assert not report.by_code("no_coincidence")
    assert not report.warnings


# --- LLM writer (fake client) ------------------------------------------------


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


def test_outreach_prompt_grounds_and_passes_coincidence():
    contact = OutreachContact(
        name="Dana Chen",
        title="Director of Product",
        company="Northwind",
        coincidence="I read your post on same-day delivery.",
    )
    system, user = build_outreach_prompt(
        contact, field="AI product management", your_name="Jordan"
    )
    assert "Chapter 4" in system
    assert "ADVICE, not a job" in system
    assert "same-day delivery" in user


def test_outreach_writer_calls_model_with_schema():
    client = _FakeClient(OutreachMessage(body="Hi Dana, ..."))
    writer = OutreachWriter(client=client)
    contact = OutreachContact(name="Dana Chen")
    writer.write(contact, field="AI PM", your_name="Jordan")
    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert call["output_format"] is OutreachMessage
