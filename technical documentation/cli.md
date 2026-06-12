# The `job-hunt` CLI

**Status:** Complete · **Scope:** a command-line front end over the orchestrator and
the individual skills. Built after Phase 5 as a presentation layer — it adds no skill
logic, only a way to drive the existing code from a terminal.

This document covers what the CLI does, how it's structured, and the reasoning behind
the choices. It assumes the skills from Phases 0–5.

---

## 1. What it is and why it exists

After Phase 5, the whole system was reachable from Python (`ApplicationOrchestrator`
and the per-skill packages), but there was no way to *use* it without writing a
script. The CLI closes that gap: a single `job-hunt` command that runs the common
workflows from a terminal.

Two principles shaped it, both inherited from the rest of the project:

- **Deterministic by default.** Every command runs with no API key. The model-backed
  steps are opt-in behind a single `--llm` flag. So a new user can try the tool
  immediately, and CI can exercise it offline.
- **Safe by default.** Profiles default to the bundled *synthetic* sample
  (`examples/sample_profile.json`), so nothing real or private is required to run —
  and no command writes anywhere except an explicit `--out` directory.

It is intentionally a **thin** layer: the CLI parses arguments, loads files into the
existing Pydantic models, calls the existing functions, and prints the results. There
is no business logic here that isn't already in a skill.

---

## 2. Stack: stdlib `argparse`, no new dependencies

The CLI is built on Python's standard-library `argparse` — no Click, Typer, or Rich.
This keeps faith with the project's "keep the stack small" rule: the only runtime
dependencies remain Pydantic and the Anthropic SDK. Output is plain text with a few
ASCII markers, which stays readable in any terminal and in captured test output.

It's registered as a console script in `pyproject.toml`:

```toml
[project.scripts]
job-hunt = "job_hunt_assistant.cli:main"
```

so `uv run job-hunt ...` (or `job-hunt ...` once installed) invokes
`job_hunt_assistant.cli:main`.

---

## 3. The commands

Four subcommands, each mapping to one slice of the system:

| Command | Skill(s) exercised | Needs `--llm`? |
|---|---|---|
| `practice` | Interview prep — practice math + canonical questions + closing questions (Ch. 5/6) | no |
| `lint` | Resume linter (Ch. 2) | no |
| `match` | Job discovery — rank postings by fit (Phase 5) | no |
| `prepare` | The full orchestrator — resume + ATS + questions + cover letter | optional |

### `practice [--questions N]`

Prints the Chapter 6 practice plan (e.g. "30 questions × 2 × 3 = 180 reps ≈ 13.5
hours"), the 12 canonical questions, and the strong closing questions from Chapter 5.
Pure data — no profile or job needed.

### `lint [--profile PATH]`

Runs `lint_profile()` and prints each finding as
`<severity> (Ch.N) <message> [where]`. Exit code is **1 if there are errors**, 0
otherwise — so it can act as a pre-send gate in a script or CI step.

### `match --jobs FILE [--profile PATH]`

Reads a JSON array of `JobPosting` objects, runs `rank_jobs()`, and prints them
best-fit first with a `★ recommended` flag (≥ 75% ATS match) and the top keyword
gaps per job.

### `prepare ... [--llm] [--email] [--out DIR]`

The capstone command. It builds a `JobPosting` (from `--job FILE.json` or inline
`--company/--role/--description[-file]`), constructs an `ApplicationOrchestrator`, and
calls `prepare()`. It prints a summary — mode, ATS score vs. target, resume size,
question count, whether a cover letter was drafted, top keyword gaps — and, if `--out`
is given, writes `resume.md`, `ats.md`, and (when present) `cover_letter.txt` to that
directory. `--email` switches the cover letter to the outbound-email format;
`--research FILE.json` supplies company research for paragraph 3.

---

## 4. The `--llm` switch — the one seam that matters

The CLI never constructs an Anthropic client at import time. Model-backed components
are built only when `--llm` is passed, by `_build_llm_components()`, which returns the
real `ResumeRewriter`, `CoverLetterWriter`, and `QuestionGenerator`. Those are then
injected into the orchestrator exactly as a test injects fakes.

The consequence is a clean two-mode design with no code duplication:

- **without `--llm`** — the orchestrator composes the deterministic halves: a
  templated resume, a real ATS score, the canonical 12 questions, no cover letter;
- **with `--llm`** — the same call path, now with model quality at each step, plus a
  drafted cover letter.

This is why the CLI tests can cover the real command paths offline: they drive `main`
through the deterministic mode, which is the identical code minus the injected
writers.

---

## 5. Input and output contracts

- **Inputs are the project's Pydantic models, as JSON.** `--job` is a `JobPosting`,
  `--jobs` a JSON array of them, `--research` a `CompanyResearch`, `--profile` a
  `CandidateProfile`. Loading goes through each model's validation, so a malformed
  file fails fast with a clear error rather than deep inside a skill.
- **Inline job flags** (`--company`, `--role`, `--description` / `--description-file`)
  are a convenience for the common case of a quick, ad-hoc posting — no file needed.
- **Output is plain text to stdout**, plus optional Markdown/text files under `--out`.
  Nothing is written unless `--out` is supplied.

---

## 6. Testing

Five CLI tests (part of the 121 total), all offline. They call `main(argv)` directly
and capture stdout via pytest's `capsys`:

| Test | Checks |
|---|---|
| `practice` | The plan math ("180 reps", "13.5 hours") and a canonical question appear. |
| `lint` | The sample profile's known findings surface; exit code 0 (warnings, no errors). |
| `match` | Best-fit job is printed before the mismatch. |
| `prepare` (inline + `--out`) | Summary fields print; `resume.md`/`ats.md` are written; no `cover_letter.txt` without `--llm`. |
| `prepare` (no job) | Exits with an error when neither `--job` nor `--company/--role` is given. |

Driving `main(argv)` in-process (rather than spawning a subprocess) keeps the tests
fast and lets them assert on captured output directly.

---

## 7. A bug worth recording

During bring-up, `prepare` referenced `ats.missing_keywords` — but that field name
belongs to `JobMatch` (discovery); the `ATSReport` field is just `missing`. The two
models both describe keyword gaps but for different callers, and the mix-up only
surfaced at runtime in the one code path that printed ATS gaps. It's a small reminder
that the CLI, as the first place several models are used *together*, is also where
cross-model naming inconsistencies show up — caught here and fixed, and now covered by
the `prepare` test.

---

## 8. What's deferred

- **A `serve`/web UI.** The orchestrator is already the single entry point, so a thin
  HTTP or TUI front end would reuse the same wiring; deferred as out of scope for a
  terminal tool.
- **Pipeline commands.** `add`/`list`/`followups` over a persisted `Pipeline` are a
  natural addition once pipeline persistence (JSON on disk) lands — the models are
  already JSON-able.
- **Richer output formatting** (tables, color) would mean a dependency like Rich;
  left out to keep the stack small.

---

## Appendix: glossary

- **`argparse`:** Python's standard-library command-line parser — subcommands, flags,
  and help text with no third-party dependency.
- **Console script:** an entry point declared in `pyproject.toml` that installs a
  named command (`job-hunt`) mapped to a Python function.
- **`capsys`:** a pytest fixture that captures `stdout`/`stderr`, letting a test assert
  on what a command printed.
- **Deterministic mode:** running the CLI without `--llm`, so every step uses the
  no-model half of each skill and needs no API key.
