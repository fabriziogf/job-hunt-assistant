"""Tests for the CLI (deterministic paths only — no API key)."""

import json

import pytest

from job_hunt_assistant.cli import main


def test_practice_prints_plan_and_questions(capsys):
    code = main(["practice", "--questions", "30"])
    out = capsys.readouterr().out
    assert code == 0
    assert "180 reps" in out
    assert "13.5 hours" in out
    assert "Tell me about yourself." in out


def test_lint_on_sample_profile(capsys):
    code = main(["lint"])
    out = capsys.readouterr().out
    assert code == 0  # sample has warnings but no errors
    assert "Jordan Rivera" in out
    assert "GPA 3.4 is below" in out


def test_match_ranks_jobs(tmp_path, capsys):
    jobs = [
        {"company": "Fit Co", "role": "PM", "description": "recommender systems "
         "LLM personalization causal inference experimentation"},
        {"company": "Mismatch", "role": "Chef", "description": "pastry baking knife"},
    ]
    jobs_file = tmp_path / "jobs.json"
    jobs_file.write_text(json.dumps(jobs))
    code = main(["match", "--jobs", str(jobs_file)])
    out = capsys.readouterr().out
    assert code == 0
    # Best fit listed first.
    assert out.index("Fit Co") < out.index("Mismatch")


def test_prepare_inline_job_writes_files(tmp_path, capsys):
    out_dir = tmp_path / "out"
    code = main([
        "prepare",
        "--company", "Northwind",
        "--role", "Senior PM",
        "--description", "recommender systems and LLM personalization",
        "--out", str(out_dir),
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "ATS match:" in out
    assert "deterministic (offline)" in out
    assert "Cover letter: skipped" in out  # no --llm
    assert (out_dir / "resume.md").exists()
    assert (out_dir / "ats.md").exists()
    assert not (out_dir / "cover_letter.txt").exists()


def test_prepare_requires_a_job():
    with pytest.raises(SystemExit):
        main(["prepare"])  # no --job and no --company/--role


def test_prepare_save_persists_and_pipeline_reads_it(tmp_path, capsys):
    ws = tmp_path / "ws"
    # Prepare + save tracks the application and writes the package.
    code = main([
        "prepare",
        "--company", "Northwind",
        "--role", "Senior PM",
        "--description", "recommender systems",
        "--save", "--workspace", str(ws),
    ])
    assert code == 0
    assert (ws / "pipeline.json").exists()
    assert list((ws / "packages").glob("*.json"))

    # The pipeline command reads the persisted state back.
    capsys.readouterr()  # clear
    code = main(["pipeline", "--workspace", str(ws)])
    out = capsys.readouterr().out
    assert code == 0
    assert "Northwind — Senior PM" in out
    assert "applied=1" in out


def test_pipeline_empty_workspace(tmp_path, capsys):
    code = main(["pipeline", "--workspace", str(tmp_path / "empty")])
    out = capsys.readouterr().out
    assert code == 0
    assert "No tracked applications" in out


def test_prepare_web_research_without_llm_stays_offline(capsys):
    # --web-research attaches a live provider, but without --llm there's no cover
    # letter writer to query it, so the run stays fully offline (no network).
    code = main([
        "prepare",
        "--company", "Northwind",
        "--role", "PM",
        "--description", "recommender systems",
        "--web-research",
    ])
    out = capsys.readouterr().out
    assert code == 0
    assert "Cover letter: skipped" in out
