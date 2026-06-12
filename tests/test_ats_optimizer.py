"""Tests for the deterministic ATS optimizer (no API key needed)."""

from datetime import date

from job_hunt_assistant import load_sample_profile
from job_hunt_assistant.ats import (
    TARGET_MATCH,
    extract_acronyms,
    extract_keywords,
    score_resume,
    score_text,
)
from job_hunt_assistant.resume import build_resume


def test_extract_keywords_captures_bigrams_and_drops_stopwords():
    kws = extract_keywords("Experience with stakeholder management and the team")
    assert "stakeholder management" in kws  # content bigram captured
    assert "stakeholder" in kws and "management" in kws
    assert "the" not in kws and "and" not in kws  # stopwords dropped
    # "experience"/"team" are boilerplate stopwords for matching purposes
    assert "team" not in kws


def test_extract_acronyms():
    acr = extract_acronyms("Strong SQL and ML skills; knowledge of SEO and teamwork")
    assert set(acr) == {"SQL", "ML", "SEO"}
    assert "teamwork" not in acr  # lowercase, not an acronym


def test_perfect_match_scores_100():
    # Resume contains every content word AND phrase from the JD.
    jd = "recommender systems and causal inference"
    resume = "Built recommender systems and applied causal inference at scale"
    report = score_text(resume, jd)
    assert report.score == 100.0
    assert report.target_met
    assert report.missing == []


def test_partial_match_lists_missing_keywords():
    jd = "Looking for Python, SQL, and Kubernetes experience"
    resume = "Strong Python and SQL background"
    report = score_text(resume, jd)
    assert not report.target_met or report.score < 100  # kubernetes missing
    assert "kubernetes" in report.missing
    assert "python" in report.matched and "sql" in report.matched


def test_missing_keywords_prioritized_by_frequency():
    jd = "personalization personalization personalization and one mention of latency"
    resume = "no relevant terms here"
    report = score_text(resume, jd)
    # The thrice-repeated term should rank ahead of the once-mentioned one.
    assert report.missing[0] == "personalization"
    assert report.missing.index("personalization") < report.missing.index("latency")


def test_target_threshold_is_75():
    assert TARGET_MATCH == 75.0
    # Stopwords between terms prevent bigrams, so only the 4 unigrams count;
    # 3 of 4 present = 75% -> meets target.
    jd = "alpha and beta or gamma to delta"
    resume = "alpha and beta or gamma"
    report = score_text(resume, jd)
    assert report.score == 75.0
    assert report.target_met


def test_acronyms_to_expand_flags_unexpanded():
    jd = "Must know SQL and ML"
    # Resume spells out ML but not SQL.
    resume = "Machine Learning (ML) and database querying"
    report = score_text(resume, jd)
    assert "SQL" in report.acronyms_to_expand
    assert "ML" not in report.acronyms_to_expand  # already expanded


def test_score_resume_accepts_assembled_resume():
    resume = build_resume(load_sample_profile(), as_of=date(2026, 6, 11))
    jd = "Seeking a product manager for recommender systems and LLM personalization"
    report = score_resume(resume, jd)
    assert 0 <= report.score <= 100
    assert "recommender" in (report.matched + report.missing)


def test_report_markdown_includes_score_and_status():
    report = score_text("python sql", "python sql kubernetes terraform")
    md = report.to_markdown()
    assert "ATS keyword match" in md
    assert "%" in md
    assert "BELOW TARGET" in md  # 2/4 = 50%
