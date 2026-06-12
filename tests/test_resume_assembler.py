"""Tests for the deterministic resume assembler (no API key needed)."""

from datetime import date

from job_hunt_assistant import load_sample_profile
from job_hunt_assistant.profile import (
    Achievement,
    CandidateProfile,
    Contact,
    Education,
    Experience,
)
from job_hunt_assistant.resume import BulletRewrite, build_resume

AS_OF = date(2026, 6, 11)


def _profile_with(*experiences: Experience, **kw) -> CandidateProfile:
    return CandidateProfile(
        contact=Contact(full_name="Test User", email="t@example.com"),
        experiences=list(experiences),
        **kw,
    )


def test_only_verified_achievements_appear():
    p = _profile_with(
        Experience(
            company="Acme",
            title="Eng",
            start=date(2023, 1, 1),
            achievements=[
                Achievement(what="Real win", measured_by="20%", verified=True),
                Achievement(what="Unverified claim", verified=False),
            ],
        )
    )
    resume = build_resume(p, as_of=AS_OF)
    texts = [b.text for e in resume.experiences for b in e.bullets]
    assert any("Real win" in t for t in texts)
    assert not any("Unverified" in t for t in texts)


def test_experiences_ordered_recent_first():
    p = _profile_with(
        Experience(
            company="Old",
            title="A",
            start=date(2015, 1, 1),
            end=date(2018, 1, 1),
            achievements=[Achievement(what="old work", measured_by="x", verified=True)],
        ),
        Experience(
            company="Current",
            title="B",
            start=date(2022, 1, 1),
            achievements=[Achievement(what="new work", measured_by="y", verified=True)],
        ),
    )
    resume = build_resume(p, as_of=AS_OF)
    assert [e.company for e in resume.experiences] == ["Current", "Old"]


def test_quantified_bullets_come_first():
    p = _profile_with(
        Experience(
            company="Acme",
            title="Eng",
            start=date(2023, 1, 1),
            achievements=[
                Achievement(what="no metric here", verified=True),
                Achievement(what="has a metric", measured_by="30%", verified=True),
            ],
        )
    )
    resume = build_resume(p, as_of=AS_OF)
    bullets = resume.experiences[0].bullets
    assert bullets[0].has_metric is True
    assert bullets[0].text.startswith("Has a metric") or "has a metric" in bullets[0].text


def test_subthreshold_gpa_dropped_but_strong_kept():
    p = _profile_with(
        Experience(company="Acme", title="Eng", start=date(2023, 1, 1)),
        education=[
            Education(institution="Strong U", gpa=3.8),
            Education(institution="Low U", gpa=3.2),
        ],
    )
    resume = build_resume(p, as_of=AS_OF)
    by_school = {e.institution: e for e in resume.education}
    assert by_school["Strong U"].gpa == 3.8
    assert by_school["Low U"].gpa is None


def test_current_role_shows_present():
    p = _profile_with(
        Experience(
            company="Acme",
            title="Eng",
            start=date(2024, 10, 1),
            achievements=[Achievement(what="x", measured_by="y", verified=True)],
        )
    )
    resume = build_resume(p, as_of=AS_OF)
    assert "Present" in resume.experiences[0].date_range


def test_length_budget_trims_weakest_bullets():
    # 40 verified bullets, but a <10yr profile budgets ~14 (1 page x 14).
    many = [
        Achievement(what=f"win {i}", measured_by=f"{i}%", verified=True)
        for i in range(40)
    ]
    p = _profile_with(
        Experience(company="Acme", title="Eng", start=date(2023, 1, 1), achievements=many)
    )
    resume = build_resume(p, as_of=AS_OF)
    total = sum(len(e.bullets) for e in resume.experiences)
    assert total == 14  # trimmed to the one-page budget


def test_findings_attached():
    resume = build_resume(load_sample_profile(), as_of=AS_OF)
    codes = {f.code for f in resume.findings}
    assert "missing_metric" in codes  # the sample's known gap surfaces here too


def test_markdown_renders_key_sections():
    md = build_resume(load_sample_profile(), as_of=AS_OF).to_markdown()
    assert "# Jordan Rivera" in md
    assert "## Experience" in md
    assert "## Education" in md


# --- Optional rewriter wiring ------------------------------------------------


class _StubRewriter:
    """Stands in for ResumeRewriter without any API call."""

    def __init__(self):
        self.seen = []

    def rewrite(self, achievement, job_description=None):
        self.seen.append(achievement.what)
        return BulletRewrite(rewritten=f"POLISHED: {achievement.what}", has_metric=True)


def test_injected_rewriter_polishes_bullets():
    p = _profile_with(
        Experience(
            company="Acme",
            title="Eng",
            start=date(2023, 1, 1),
            achievements=[Achievement(what="did a thing", measured_by="5%", verified=True)],
        )
    )
    rw = _StubRewriter()
    resume = build_resume(p, as_of=AS_OF, rewriter=rw)
    assert resume.experiences[0].bullets[0].text == "POLISHED: did a thing"
    assert rw.seen == ["did a thing"]
