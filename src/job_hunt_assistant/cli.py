"""Command-line interface over the Job Hunt Assistant (Phase 5+).

A thin, dependency-free (stdlib ``argparse``) front end on top of
``ApplicationOrchestrator`` and the individual skills. It runs **deterministically
by default** so every command works with no API key; pass ``--llm`` to enable the
model-backed steps (resume rewriting, cover letter, tailored questions), which
require ``ANTHROPIC_API_KEY``.

Profiles default to the bundled synthetic sample, so the CLI is runnable
out-of-the-box without touching any real personal data.

Examples::

    job-hunt practice
    job-hunt lint --profile profiles/my_profile.json
    job-hunt match --jobs jobs.json
    job-hunt prepare --company Northwind --role "Senior PM" \\
        --description-file jd.txt --out ./out
    job-hunt prepare --job job.json --llm --out ./out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from job_hunt_assistant.ats import score_resume
from job_hunt_assistant.discovery import JobPosting, rank_jobs
from job_hunt_assistant.findings import FindingsReport, Severity
from job_hunt_assistant.interview import closing_questions, practice_plan
from job_hunt_assistant.interview.questions import canonical_questions
from job_hunt_assistant.orchestration import ApplicationOrchestrator
from job_hunt_assistant.profile import CandidateProfile
from job_hunt_assistant.research.company import CompanyResearch
from job_hunt_assistant.resume import build_resume, lint_profile
from job_hunt_assistant.samples import load_profile, load_sample_profile

_SEVERITY_MARK = {
    Severity.ERROR: "✗ ERROR",
    Severity.WARNING: "! WARN ",
    Severity.INFO: "· info ",
}


# --- argument loaders --------------------------------------------------------


def _load_profile(path: str | None) -> CandidateProfile:
    if path is None:
        return load_sample_profile()
    return load_profile(path)


def _job_from_args(args: argparse.Namespace) -> JobPosting:
    """Build a JobPosting from --job FILE.json, or from inline flags."""
    if getattr(args, "job", None):
        return JobPosting.model_validate_json(Path(args.job).read_text())
    if not (args.company and args.role):
        raise SystemExit(
            "error: provide --job FILE.json, or both --company and --role "
            "(plus --description / --description-file)."
        )
    description = ""
    if args.description_file:
        description = Path(args.description_file).read_text()
    elif args.description:
        description = args.description
    return JobPosting(company=args.company, role=args.role, description=description)


def _load_research(path: str | None) -> CompanyResearch | None:
    if not path:
        return None
    return CompanyResearch.model_validate_json(Path(path).read_text())


def _print_findings(report: FindingsReport) -> None:
    if not report.findings:
        print("  (no findings)")
        return
    for f in report.findings:
        where = f" [{f.where}]" if f.where else ""
        print(f"  {_SEVERITY_MARK[f.severity]} (Ch.{f.chapter}) {f.message}{where}")


# --- LLM component wiring (only when --llm) ----------------------------------


def _build_llm_components() -> dict:
    """Construct the real Anthropic-backed writers. Requires ANTHROPIC_API_KEY."""
    try:
        from job_hunt_assistant.coverletter.writer import CoverLetterWriter
        from job_hunt_assistant.interview.generator import QuestionGenerator
        from job_hunt_assistant.resume import ResumeRewriter

        return {
            "rewriter": ResumeRewriter(),
            "cover_letter_writer": CoverLetterWriter(),
            "question_generator": QuestionGenerator(),
        }
    except Exception as exc:  # pragma: no cover - defensive
        raise SystemExit(f"error: could not initialize LLM components: {exc}")


# --- commands ----------------------------------------------------------------


def cmd_practice(args: argparse.Namespace) -> int:
    plan = practice_plan(args.questions)
    print("Interview practice plan (Chapter 6)")
    print(" ", plan.summary())
    print("\nThe 12 questions you'll almost certainly be asked:")
    for i, q in enumerate(canonical_questions(), 1):
        print(f"  {i:2}. {q.text}")
    print("\nStrong questions to ask them (Chapter 5):")
    for q in closing_questions():
        print(f"  - {q}")
    return 0


def cmd_lint(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)
    print(f"Resume lint for {profile.contact.full_name} (Chapter 2)")
    report = lint_profile(profile)
    _print_findings(report)
    return 1 if report.has_errors else 0


def cmd_match(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)
    raw = json.loads(Path(args.jobs).read_text())
    jobs = [JobPosting.model_validate(x) for x in raw]
    ranked = rank_jobs(profile, jobs)
    print(f"Job matches for {profile.contact.full_name} (best fit first):\n")
    for m in ranked:
        flag = "★ recommended" if m.recommended else ""
        print(f"  {m.score:5.1f}%  {m.job.company} — {m.job.role}  {flag}")
        if m.missing_keywords:
            print(f"          top gaps: {', '.join(m.missing_keywords[:6])}")
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    profile = _load_profile(args.profile)
    job = _job_from_args(args)
    research = _load_research(args.research)

    components = _build_llm_components() if args.llm else {}
    orch = ApplicationOrchestrator(profile, **components)

    from job_hunt_assistant.coverletter.models import LetterFormat

    fmt = LetterFormat.EMAIL if args.email else LetterFormat.LETTER
    pkg = orch.prepare(job, research=research, fmt=fmt)

    print(f"Application package: {job.role} at {job.company}")
    print(f"  Mode: {'LLM-enhanced' if args.llm else 'deterministic (offline)'}")
    print(f"  ATS match: {pkg.ats.score:.0f}% (target {pkg.ats.target:.0f}%) — "
          f"{'PASS' if pkg.ats.target_met else 'below target'}")
    print(f"  Resume: {sum(len(e.bullets) for e in pkg.resume.experiences)} bullets "
          f"across {len(pkg.resume.experiences)} roles")
    print(f"  Interview questions: {pkg.question_bank.count}")
    print(f"  Cover letter: {'drafted' if pkg.cover_letter else 'skipped (use --llm)'}")

    if pkg.ats.missing:
        print(f"  Top keyword gaps: {', '.join(pkg.ats.missing[:8])}")

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "resume.md").write_text(pkg.resume.to_markdown())
        (out / "ats.md").write_text(pkg.ats.to_markdown())
        if pkg.cover_letter:
            (out / "cover_letter.txt").write_text(pkg.cover_letter.full_text())
        print(f"\n  Wrote files to {out}/")
    return 0


# --- parser ------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="job-hunt",
        description="AI job-hunt assistant grounded in Laszlo Bock's Apply Within.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_profile(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--profile",
            help="Path to a profile JSON (defaults to the bundled sample).",
        )

    def add_job(p: argparse.ArgumentParser) -> None:
        p.add_argument("--job", help="Path to a JobPosting JSON file.")
        p.add_argument("--company", help="Company name (inline job).")
        p.add_argument("--role", help="Role title (inline job).")
        p.add_argument("--description", help="Job description text (inline).")
        p.add_argument("--description-file", help="Path to a job description file.")

    p_practice = sub.add_parser("practice", help="Show the interview practice plan.")
    p_practice.add_argument("--questions", type=int, default=30)
    p_practice.set_defaults(func=cmd_practice)

    p_lint = sub.add_parser("lint", help="Run the resume linter on a profile.")
    add_profile(p_lint)
    p_lint.set_defaults(func=cmd_lint)

    p_match = sub.add_parser("match", help="Rank jobs by fit against a profile.")
    add_profile(p_match)
    p_match.add_argument("--jobs", required=True, help="JSON array of JobPostings.")
    p_match.set_defaults(func=cmd_match)

    p_prep = sub.add_parser("prepare", help="Build a full application package.")
    add_profile(p_prep)
    add_job(p_prep)
    p_prep.add_argument("--research", help="Path to a CompanyResearch JSON file.")
    p_prep.add_argument("--llm", action="store_true", help="Enable model-backed steps.")
    p_prep.add_argument("--email", action="store_true", help="Outbound email format.")
    p_prep.add_argument("--out", help="Directory to write the package files to.")
    p_prep.set_defaults(func=cmd_prepare)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
