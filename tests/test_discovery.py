"""Tests for job discovery & matching (Phase 5)."""

from datetime import date

from job_hunt_assistant import JobPosting, load_sample_profile, match_job, rank_jobs
from job_hunt_assistant.pipeline import CompanyTier

AS_OF = date(2026, 6, 11)


def test_match_job_scores_against_posting():
    profile = load_sample_profile()
    job = JobPosting(
        company="Northwind",
        role="Senior PM",
        description="Own recommender systems and LLM personalization; run A/B "
        "experiments and apply causal inference.",
    )
    match = match_job(profile, job, as_of=AS_OF)
    assert 0 <= match.score <= 100
    # The sample profile genuinely has recommender/personalization experience.
    assert "recommender" in (match.matched_keywords + match.missing_keywords)


def test_rank_jobs_orders_best_fit_first():
    profile = load_sample_profile()
    strong = JobPosting(
        company="Fit Co",
        role="PM",
        description="recommender systems, LLM personalization, causal inference, "
        "experimentation, product strategy",
    )
    weak = JobPosting(
        company="Mismatch Co",
        role="Chef",
        description="pastry, baking, knife skills, menu design, restaurant service",
    )
    ranked = rank_jobs(profile, [weak, strong], as_of=AS_OF)
    assert ranked[0].job.company == "Fit Co"
    assert ranked[0].score > ranked[1].score


def test_recommended_flag_tracks_target():
    profile = load_sample_profile()
    weak = JobPosting(company="X", role="Chef", description="pastry baking knives")
    match = match_job(profile, weak, as_of=AS_OF)
    assert not match.recommended  # clearly below the 75% target


def test_job_posting_defaults_to_b_tier():
    job = JobPosting(company="X", role="PM", description="...")
    assert job.tier is CompanyTier.B
