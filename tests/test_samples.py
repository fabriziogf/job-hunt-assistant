"""Tests for the bundled sample profile fixture."""

from job_hunt_assistant import load_sample_profile


def test_sample_profile_loads_and_validates():
    p = load_sample_profile()
    assert p.contact.full_name == "Jordan Rivera"
    assert len(p.experiences) == 2
    assert len(p.education) == 2


def test_sample_has_verified_material_and_a_quantification_gap():
    p = load_sample_profile()
    # All sample achievements are verified...
    assert len(p.verified_achievements()) == 5
    # ...but one is intentionally missing a measurable Y, to exercise the
    # Resume Builder's gap detection.
    assert len(p.unquantified_achievements()) == 1


def test_sample_exercises_gpa_threshold_rule():
    p = load_sample_profile()
    by_school = {e.institution: e for e in p.education}
    assert by_school["University of Washington"].gpa_meets_resume_threshold
    # 3.4 < 3.5 -> Ch.2 says leave it off.
    assert not by_school["State University"].gpa_meets_resume_threshold


def test_sample_carries_brands_for_namedropping():
    p = load_sample_profile()
    brands = p.all_brands()
    assert "Salesforce" in brands
    assert "Northwind Commerce" in brands
