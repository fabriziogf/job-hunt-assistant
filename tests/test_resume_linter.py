"""Tests for the deterministic resume linter."""

from datetime import date

from job_hunt_assistant import load_sample_profile
from job_hunt_assistant.profile import (
    Achievement,
    CandidateProfile,
    Contact,
    Education,
    Experience,
)
from job_hunt_assistant.resume import Severity, lint_profile, recommended_max_pages

AS_OF = date(2026, 6, 11)  # fixed clock so length/year checks are deterministic


def test_sample_profile_flags_its_known_gaps():
    report = lint_profile(load_sample_profile(), as_of=AS_OF)
    # The fixture has exactly one unquantified verified achievement.
    assert len(report.by_code("missing_metric")) == 1
    # And one sub-3.5 GPA (State University, 3.4).
    gpa = report.by_code("gpa_below_threshold")
    assert len(gpa) == 1
    assert "State University" in (gpa[0].where or "")


def test_every_finding_cites_a_chapter():
    report = lint_profile(load_sample_profile(), as_of=AS_OF)
    assert report.findings
    assert all(1 <= f.chapter <= 8 for f in report.findings)


def test_missing_email_is_an_error():
    profile = CandidateProfile(
        contact=Contact(full_name="No Email", phone="555-0100"),
        experiences=[
            Experience(company="Acme", title="Eng", start=date(2023, 1, 1))
        ],
    )
    report = lint_profile(profile, as_of=AS_OF)
    assert report.has_errors
    assert report.by_code("missing_email")[0].severity is Severity.ERROR


def test_recommended_pages_one_per_decade():
    recent = CandidateProfile(
        contact=Contact(full_name="X", email="x@y.com"),
        experiences=[Experience(company="A", title="T", start=date(2020, 1, 1))],
    )
    veteran = CandidateProfile(
        contact=Contact(full_name="X", email="x@y.com"),
        experiences=[Experience(company="A", title="T", start=date(2004, 1, 1))],
    )
    assert recommended_max_pages(recent, as_of=AS_OF) == 1
    assert recommended_max_pages(veteran, as_of=AS_OF) == 3  # ~22 years -> 3 pages


def test_award_without_context_flagged():
    profile = CandidateProfile(
        contact=Contact(full_name="X", email="x@y.com"),
        education=[Education(institution="State U", awards=["Smith Prize"])],
    )
    report = lint_profile(profile, as_of=AS_OF)
    assert report.by_code("award_lacks_context")


def test_honesty_gate_counts_unverified():
    profile = CandidateProfile(
        contact=Contact(full_name="X", email="x@y.com"),
        experiences=[
            Experience(
                company="Acme",
                title="Eng",
                start=date(2023, 1, 1),
                achievements=[
                    Achievement(what="Real thing", measured_by="20%", verified=True),
                    Achievement(what="Unconfirmed claim", verified=False),
                ],
            )
        ],
    )
    report = lint_profile(profile, as_of=AS_OF)
    note = report.by_code("unverified_excluded")
    assert note and "1 achievement" in note[0].message


def test_clean_profile_has_no_errors():
    profile = CandidateProfile(
        contact=Contact(full_name="Clean", email="c@y.com", phone="555-0100"),
        experiences=[
            Experience(
                company="Acme",
                title="Eng",
                start=date(2022, 1, 1),
                achievements=[
                    Achievement(what="Shipped X", measured_by="30% faster", verified=True)
                ],
            )
        ],
        education=[Education(institution="State U", gpa=3.9)],
    )
    report = lint_profile(profile, as_of=AS_OF)
    assert not report.has_errors
