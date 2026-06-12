"""Tests for the playbook loader."""

import pytest

from job_hunt_assistant import PLAYBOOK, AgentSkill, ChapterPrinciples


def test_all_eight_chapters_present():
    chapters = PLAYBOOK.all_chapters()
    assert [c.number for c in chapters] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert all(isinstance(c, ChapterPrinciples) for c in chapters)
    assert all(c.core_principle for c in chapters)


def test_every_skill_maps_to_valid_chapters():
    for skill in AgentSkill:
        chapters = PLAYBOOK.for_skill(skill)
        assert chapters, f"{skill} has no chapters"
        for c in chapters:
            assert 1 <= c.number <= 8


def test_resume_builder_grounds_in_chapters_1_and_2():
    assert PLAYBOOK.chapters_for_skill(AgentSkill.RESUME_BUILDER) == (1, 2)


def test_chapter_2_carries_the_xyz_formula():
    ch2 = PLAYBOOK.chapter(2)
    assert any("[X]" in f and "[Y]" in f and "[Z]" in f for f in ch2.formulas)


def test_unknown_chapter_raises():
    with pytest.raises(KeyError):
        PLAYBOOK.chapter(99)


def test_as_prompt_includes_skill_and_chapter_content():
    prompt = PLAYBOOK.as_prompt(AgentSkill.NEGOTIATION)
    assert "negotiation" in prompt
    assert "Chapter 8" in prompt
    # A concrete Ch. 8 rule should surface in the rendered block.
    assert "writing" in prompt.lower()


def test_as_prompt_renders_formulas_and_stats():
    block = PLAYBOOK.chapter(4).as_prompt()
    assert "Chapter 4" in block
    assert "5-10x" in block  # the referral stat
