"""Tests for the cover letter writer (fake client — no API key needed)."""

from datetime import date

from job_hunt_assistant import CompanyFact, CompanyResearch, load_sample_profile
from job_hunt_assistant.coverletter import (
    CoverLetter,
    LetterFormat,
    build_cover_letter_prompt,
)
from job_hunt_assistant.coverletter.writer import CoverLetterWriter
from job_hunt_assistant.profile import (
    Achievement,
    CandidateProfile,
    Contact,
    Experience,
)


# --- Fakes -------------------------------------------------------------------


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


def _research() -> CompanyResearch:
    return CompanyResearch(
        company="Northwind Commerce",
        hiring_manager_name="Dana Chen",
        hiring_manager_title="Director of Product",
        facts=[CompanyFact(text="launched a same-day delivery network", source="blog")],
    )


# --- Prompt construction (pure) ----------------------------------------------


def test_prompt_grounds_in_chapter_3_and_honesty_rules():
    profile = load_sample_profile()
    system, user = build_cover_letter_prompt(
        profile, company="Northwind Commerce", role="Product Manager", research=_research()
    )
    assert "Chapter 3" in system
    assert "NEVER invent facts about the company" in system
    assert "Northwind Commerce" in user
    assert "same-day delivery network" in user  # research fact passed through
    assert "Dana Chen" in user  # hiring manager name passed through


def test_prompt_only_uses_verified_achievements():
    profile = CandidateProfile(
        contact=Contact(full_name="Test User", email="t@example.com"),
        experiences=[
            Experience(
                company="Acme",
                title="PM",
                start=date(2023, 1, 1),
                achievements=[
                    Achievement(what="Real verified win", measured_by="20%", verified=True),
                    Achievement(what="Secret unverified claim", verified=False),
                ],
            )
        ],
    )
    _, user = build_cover_letter_prompt(profile, company="Acme", role="PM")
    assert "Real verified win" in user
    assert "Secret unverified claim" not in user


def test_prompt_warns_when_no_research():
    _, user = build_cover_letter_prompt(
        load_sample_profile(), company="Acme", role="PM", research=None
    )
    assert "none provided" in user.lower()
    assert "do not invent" in user.lower()


def test_email_format_requests_subject_line():
    _, user = build_cover_letter_prompt(
        load_sample_profile(),
        company="Acme",
        role="PM",
        fmt=LetterFormat.EMAIL,
    )
    assert "EMAIL" in user
    assert "subject line" in user.lower()


# --- Writer behavior ---------------------------------------------------------


def test_write_calls_model_with_schema_and_records_format():
    drafted = CoverLetter(
        salutation="Dear Ms. Chen,",
        paragraphs=["a", "b", "c", "d"],
        signoff="Sincerely,",
    )
    client = _FakeClient(drafted)
    writer = CoverLetterWriter(client=client)

    letter = writer.write(
        load_sample_profile(),
        company="Northwind Commerce",
        role="Product Manager",
        research=_research(),
        fmt=LetterFormat.EMAIL,
    )

    call = client.messages.calls[0]
    assert call["model"] == "claude-opus-4-8"
    assert call["output_format"] is CoverLetter
    assert letter.format is LetterFormat.EMAIL  # requested format recorded


def test_full_text_renders_email_with_subject():
    letter = CoverLetter(
        format=LetterFormat.EMAIL,
        subject="PM application — recommender systems",
        salutation="Hi Dana,",
        paragraphs=["one", "two", "three", "four"],
        signoff="Best,\nJordan",
    )
    text = letter.full_text()
    assert text.startswith("Subject: PM application")
    assert "Hi Dana," in text
