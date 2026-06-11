"""Tests for the candidate profile store — verifying the Ch. 2 rules it encodes."""

from datetime import date

import pytest

from job_hunt_assistant import (
    Achievement,
    CandidateProfile,
    Contact,
    Education,
    Experience,
    Skill,
)


def test_xyz_bullet_renders_full_formula():
    a = Achievement(
        what="Managed a $31,000 Spring 2026 budget",
        measured_by="a 5% return over the year",
        how="investing $10,000 of idle funds in high-yield capital notes",
        verified=True,
    )
    assert a.is_quantified
    assert a.is_complete
    bullet = a.to_xyz_bullet()
    assert bullet.startswith("Managed a $31,000")
    assert "as measured by a 5% return over the year" in bullet
    assert "by investing $10,000" in bullet
    assert bullet.endswith(".")


def test_unquantified_achievement_flagged():
    a = Achievement(what="Managed sorority budget", verified=True)
    assert not a.is_quantified
    assert not a.is_complete


def test_experience_rejects_end_before_start():
    with pytest.raises(ValueError):
        Experience(
            company="Acme",
            title="Analyst",
            start=date(2024, 1, 1),
            end=date(2023, 1, 1),
        )


def test_gpa_threshold_rule():
    # Ch. 2: 3.5+ shows; below is left off.
    assert Education(institution="X", gpa=3.7).gpa_meets_resume_threshold
    assert not Education(institution="X", gpa=3.2).gpa_meets_resume_threshold
    # Different scale normalizes to 4.0.
    assert Education(institution="X", gpa=9.0, gpa_scale=10.0).gpa_meets_resume_threshold


def test_hardship_exceptions():
    plain = Education(institution="X")
    assert not plain.has_mentionable_hardship
    first_gen = Education(institution="X", first_generation=True)
    assert first_gen.has_mentionable_hardship


def _sample_profile() -> CandidateProfile:
    return CandidateProfile(
        contact=Contact(full_name="Jane Doe", email="jane@example.com"),
        experiences=[
            Experience(
                company="Google",
                title="Analyst",
                start=date(2022, 6, 1),
                brands=["Pfizer", "Nike"],
                achievements=[
                    Achievement(
                        what="Improved portfolio performance",
                        measured_by="12% ($1.2M) over one year",
                        verified=True,
                    ),
                    Achievement(what="Helped with reporting", verified=True),
                    Achievement(what="Unverified claim", verified=False),
                ],
            )
        ],
        education=[Education(institution="State U", gpa=3.8)],
        skills=[Skill(name="SEO", acronym_expansion="Search Engine Optimization")],
    )


def test_verified_and_unquantified_filters():
    p = _sample_profile()
    assert len(p.all_achievements()) == 3
    # Only the two verified ones count as honest material.
    assert len(p.verified_achievements()) == 2
    # One verified achievement still lacks a measurable Y.
    assert len(p.unquantified_achievements()) == 1


def test_brand_dedup_includes_company_names():
    p = _sample_profile()
    brands = p.all_brands()
    assert brands == ["Google", "Pfizer", "Nike"]


def test_round_trip_json():
    p = _sample_profile()
    restored = CandidateProfile.from_json(p.to_json())
    assert restored == p
