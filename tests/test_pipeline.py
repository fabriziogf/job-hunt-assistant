"""Tests for the Application Pipeline Tracker (Chapter 7)."""

from datetime import date

from job_hunt_assistant.pipeline import (
    Application,
    ApplicationStatus,
    CompanyTier,
    Pipeline,
    applications_needed,
    project_funnel,
    recommended_application_order,
)


# --- Volume math -------------------------------------------------------------


def test_funnel_projection_matches_playbook_ratios():
    proj = project_funnel(100)
    assert proj.expected_first_rounds == 5.0
    assert proj.expected_final_rounds == 1.5
    assert proj.expected_offers == 1.0


def test_applications_needed_is_about_100_per_offer():
    assert applications_needed(1) == 100
    assert applications_needed(2) == 200


# --- Follow-up cadence -------------------------------------------------------


def test_followup_due_after_two_weeks_within_window():
    app = Application(
        company="Acme", role="PM", date_applied=date(2026, 5, 1),
        status=ApplicationStatus.APPLIED,
    )
    # 15 days later, no touch since -> due.
    assert app.followup_due(date(2026, 5, 16))
    # 10 days later -> not yet.
    assert not app.followup_due(date(2026, 5, 11))


def test_followup_stops_after_six_weeks():
    app = Application(
        company="Acme", role="PM", date_applied=date(2026, 5, 1),
        status=ApplicationStatus.APPLIED,
    )
    # 50 days out is past the 6-week window.
    assert not app.followup_due(date(2026, 6, 20))


def test_closed_application_never_due():
    app = Application(
        company="Acme", role="PM", date_applied=date(2026, 5, 1),
        status=ApplicationStatus.CLOSED,
    )
    assert not app.followup_due(date(2026, 5, 16))


def test_should_reapply_after_three_months_silent():
    app = Application(
        company="Acme", role="PM", date_applied=date(2026, 1, 1),
        status=ApplicationStatus.APPLIED,
    )
    assert app.should_reapply(date(2026, 4, 15))  # >90 days
    assert not app.should_reapply(date(2026, 2, 1))  # <90 days


# --- Sequencing --------------------------------------------------------------


def test_b_tier_companies_come_first():
    apps = [
        Application(company="Dream", role="PM", date_applied=date(2026, 5, 1), tier=CompanyTier.A),
        Application(company="Middle", role="PM", date_applied=date(2026, 5, 1), tier=CompanyTier.B),
        Application(company="Fallback", role="PM", date_applied=date(2026, 5, 1), tier=CompanyTier.C),
    ]
    ordered = recommended_application_order(apps)
    assert [a.company for a in ordered] == ["Middle", "Dream", "Fallback"]


# --- Pipeline aggregation ----------------------------------------------------


def test_pipeline_counts_open_and_due():
    pipe = Pipeline()
    pipe.add(Application(company="A", role="PM", date_applied=date(2026, 5, 1), status=ApplicationStatus.APPLIED))
    pipe.add(Application(company="B", role="PM", date_applied=date(2026, 5, 1), status=ApplicationStatus.OFFER))
    pipe.add(Application(company="C", role="PM", date_applied=date(2026, 5, 1), status=ApplicationStatus.CLOSED))

    counts = pipe.counts_by_status()
    assert counts[ApplicationStatus.APPLIED] == 1
    assert counts[ApplicationStatus.OFFER] == 1
    assert len(pipe.open_applications()) == 1  # only the APPLIED one
    assert len(pipe.due_followups(date(2026, 5, 20))) == 1
