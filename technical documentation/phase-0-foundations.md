# Phase 0 — Foundations

**Status:** Complete · **Scope:** project scaffold, candidate profile store, playbook
loader, sample profile fixture.

This document summarizes what Phase 0 built, how the pieces fit together, and *why*
each decision was made. It assumes you can read Python but explains the
domain-specific and library-specific choices as they come up.

---

## 1. What Phase 0 is for

The Job Hunt Assistant is a set of focused **skills** (Resume Builder, Cover Letter
Writer, Interview Prep Coach, etc.), each grounded in a chapter of Laszlo Bock's
*Apply Within* playbook. Phase 0 builds none of those skills. Instead it builds the
two things *every* skill will depend on:

1. A **candidate profile store** — one validated, in-memory representation of the
   job seeker's real experience and achievements. The single source of truth.
2. A **playbook loader** — a structured, queryable version of the playbook's advice
   that any skill can inject into its prompts so its output stays grounded in the
   guide rather than in generic model intuition.

Plus the supporting scaffolding: a packaged Python project, a test suite, and a
realistic sample profile to develop against.

The guiding principle, taken straight from the playbook: **never fabricate candidate
data.** Several design decisions below exist specifically to make fabrication hard.

---

## 2. Project scaffold

### Stack

| Choice | What it is | Why |
|--------|-----------|-----|
| **Python 3.12** | Language runtime | Matches the existing personal "vibe-coding" stack; modern typing syntax (`str \| None`). |
| **`uv`** | A fast Python package & environment manager (a single tool replacing `pip` + `venv` + `pip-tools`) | Speed and a reproducible lockfile (`uv.lock`) with near-zero config. |
| **Pydantic v2** | A data-validation library: you declare data shapes as Python classes, and it validates/parses/serializes them | Gives us a typed schema *and* JSON (de)serialization *and* validation from one class definition. |
| **pytest** | Test framework | Standard, low-ceremony. |

### Layout

The project uses a **`src/` layout** — the package lives in
`src/job_hunt_assistant/` rather than at the repo root.

```
job-hunt-assistant/
├── src/job_hunt_assistant/   # the importable package
│   ├── __init__.py           # public API surface
│   ├── profile.py            # candidate profile store
│   ├── playbook.py           # playbook loader
│   └── samples.py            # profile loaders
├── examples/
│   └── sample_profile.json   # synthetic fixture (committed)
├── profiles/                 # real profiles (gitignored)
├── tests/
├── technical documentation/
├── pyproject.toml            # project metadata + dependencies
└── uv.lock                   # pinned dependency versions
```

**Why `src/` layout?** It prevents a common bug where tests accidentally import the
package from the working directory instead of the actually-installed version. With
`src/`, the package *must* be installed (here, in editable/develop mode via
`uv sync`) for imports to resolve, so tests run against the real installed artifact.
This is the widely-recommended Python packaging convention.

### A note on what is *not* committed

The source PDF (`guide.pdf`) and any real candidate profile (`profiles/`) are
`.gitignore`d. The repository is **public**, and both are sensitive:

- `guide.pdf` is Laszlo Bock's copyrighted work — we reference and paraphrase it but
  do not redistribute it.
- A real profile contains personal contact info and employment history.

This split (public synthetic data, local private data) recurs throughout Phase 0.

---

## 3. The candidate profile store (`profile.py`)

This is the data model for everything the agent knows about a candidate. It is a
tree of Pydantic models:

```
CandidateProfile
├── contact: Contact
├── experiences: list[Experience]
│   └── achievements: list[Achievement]   # the X/Y/Z bullets
├── education: list[Education]
└── skills: list[Skill]
```

### The central idea: the X/Y/Z achievement

The playbook's Chapter 2 reduces a good resume bullet to one formula:

> **Accomplished [X] as measured by [Y] by doing [Z].**

- **X** = what you achieved
- **Y** = how it's measured (a number, %, $, or time)
- **Z** = how you actually did it

This formula is modeled directly as the `Achievement` class:

```python
class Achievement(BaseModel):
    what: str                       # X — required
    measured_by: str | None = None  # Y — the metric
    how: str | None = None          # Z — the method
    verified: bool = False
    tags: list[str] = []
```

`measured_by` and `how` are **optional** on purpose. Real profile data often starts
incomplete — someone knows *what* they did but hasn't yet pinned down the metric. The
model captures that partial state rather than forcing made-up numbers. Two derived
properties expose the gap so a later skill can act on it:

- `is_quantified` → is there a measurable **Y**?
- `is_complete` → are all three of X/Y/Z present?

A `to_xyz_bullet()` method stitches whatever parts exist into a single sentence. It's
a deterministic starting point; the Resume Builder (Phase 1) will rewrite it into the
candidate's voice using an LLM.

### Enforcing "never fabricate" with the `verified` flag

Every `Achievement` carries a `verified: bool` defaulting to `False`. The convention
is: **only a human sets `verified=True`.** The agent may *draft* achievements, but
until a person confirms one, it is not treated as usable material.

`CandidateProfile` then exposes filtered views built on this flag:

- `verified_achievements()` — the honest set the skills are allowed to draw on.
- `unquantified_achievements()` — verified achievements still missing a metric;
  i.e. the concrete to-do list for the Resume Builder.

This turns an abstract rule ("don't lie") into a structural constraint: skills are
written to consume `verified_achievements()`, so unconfirmed data simply isn't in the
pipeline.

### Encoding the rest of Chapter 2 as code

Several smaller playbook rules are encoded as model fields or properties, so the
advice lives next to the data rather than being re-derived ad hoc:

| Playbook rule (Ch. 2) | Where it lives |
|----------------------|----------------|
| "Name-drop recognizable brands — recruiters search by company name." | `Experience.brands`, aggregated and de-duplicated by `CandidateProfile.all_brands()`. |
| "Show a GPA only if 3.5+." | `Education.gpa_meets_resume_threshold` (normalizes any `gpa_scale` to a 4.0 baseline first). |
| The "hardship rule" — only three hardships help a job application. | Three explicit booleans on `Education` (`self_financed_third_plus`, `worked_during_school`, `first_generation`) and a `has_mentionable_hardship` helper. |
| ATS rule: "spell out an acronym once." | `Skill.acronym_expansion` (e.g. `name="SEO"`, `acronym_expansion="Search Engine Optimization"`). |

A small amount of validation guards data integrity — e.g. a Pydantic
`field_validator` rejects an `Experience` whose `end` date precedes its `start`.

### Serialization

`to_json()` / `from_json()` wrap Pydantic's `model_dump_json` /
`model_validate_json`. Because the whole profile is a Pydantic tree, a profile can
round-trip to disk as JSON and reload with full validation — which is exactly how the
sample fixture and real profiles are stored.

---

## 4. The playbook loader (`playbook.py`)

### The problem it solves

We want every skill's advice to trace back to the playbook. But we **cannot ship the
copyrighted PDF**, and even if we could, dumping raw PDF text into a prompt is noisy
and unstructured.

### The approach: distilled, structured principles

`playbook.py` holds a hand-curated, **paraphrased** distillation of all 8 chapters.
Each chapter is a `ChapterPrinciples` object:

```python
class ChapterPrinciples(BaseModel):
    number: int
    title: str
    core_principle: str
    rules: list[str]      # actionable do/don'ts
    formulas: list[str]   # memorable templates (e.g. the X/Y/Z formula)
    stats: list[str]      # grounding numbers (e.g. "referrals get hired 5-10x more")
```

This is paraphrase, not reproduction — short factual rules ("11pt minimum font") plus
our own restatement of the ideas. It keeps us clear of redistributing the source
while preserving the substance.

### Mapping skills to chapters

An `AgentSkill` enum lists the agent's seven skills, and a dictionary maps each to the
chapters that ground it:

```python
Skill.RESUME_BUILDER  → (1, 2)
Skill.ATS_OPTIMIZER   → (2,)
Skill.COVER_LETTER    → (3,)
Skill.NETWORKING      → (4,)
Skill.INTERVIEW_PREP  → (5, 6)
Skill.PIPELINE_TRACKER→ (7,)
Skill.NEGOTIATION     → (8,)
```

### The key method: `as_prompt(skill)`

The loader's payoff is `PLAYBOOK.as_prompt(skill)`, which renders the relevant
chapters into a ready-to-inject text block — a header naming the skill, then each
chapter's principle, formulas, rules, and stats as Markdown. A Phase 1 skill builds
its system prompt by calling this method, so the guidance is **chapter-cited and
consistent** instead of hand-copied into each skill.

`PLAYBOOK` is exposed as a module-level singleton (the principles are static
read-only data), so callers just `from job_hunt_assistant import PLAYBOOK`.

### A naming decision worth recording

`profile.py` already had a `Skill` class meaning *a candidate competency* (e.g.
"Python"). The playbook's enum also wanted to be called `Skill`, meaning *an agent
capability*. Two different `Skill`s in the same public namespace is a trap. We renamed
the playbook enum to **`AgentSkill`**, which is also just clearer about what it is.

---

## 5. Sample profiles & loaders (`samples.py`, `examples/`, `profiles/`)

To develop and test skills we need a realistic profile — but committing a real one to
a public repo leaks PII. The resolution is a **hybrid**:

- **`examples/sample_profile.json`** — a *synthetic*, fictional candidate ("Jordan
  Rivera"), committed to the repo. It is generated *through* the schema (not
  hand-written) so it is guaranteed valid. It deliberately includes two "teaching"
  cases:
  - a sub-3.5 GPA (3.4) → exercises the `gpa_meets_resume_threshold` rule, and
  - one achievement with no `measured_by` → exercises quantification-gap detection.
- **`profiles/`** — a *gitignored* directory holding the real profile
  (`my_profile.json`), generated from the user's actual résumé. It never enters
  version control.

`samples.py` provides the loaders:

- `load_sample_profile()` → loads the bundled synthetic fixture (path resolved
  relative to the repo root, so it works regardless of working directory).
- `load_profile(path)` → loads and validates any profile JSON, used for the local
  real profile.

Because loading goes through `CandidateProfile.from_json`, every load is also a
validation: a malformed profile fails fast at load time rather than deep inside a
skill.

---

## 6. Public API (`__init__.py`)

The package's `__init__.py` re-exports the curated surface so consumers import from
one place:

```python
from job_hunt_assistant import (
    CandidateProfile, Contact, Experience, Achievement, Education, Skill,  # profile
    PLAYBOOK, Playbook, AgentSkill, ChapterPrinciples,                     # playbook
    load_sample_profile, load_profile,                                     # loaders
)
```

Keeping the API explicit (via `__all__`) means internal refactors won't accidentally
change what downstream skills can rely on.

---

## 7. Testing

19 tests across three files, all passing:

| File | Covers |
|------|--------|
| `test_profile.py` | X/Y/Z bullet rendering, quantification/completeness flags, the GPA threshold and hardship rules, the date validator, the verified/unquantified filters, brand de-duplication, JSON round-trip. |
| `test_playbook.py` | all 8 chapters present, every skill maps to valid chapters, Ch. 2 carries the X/Y/Z formula, unknown-chapter error, `as_prompt` content. |
| `test_samples.py` | the fixture loads and validates, and its deliberate teaching cases (GPA gap, quantification gap, brands) are present. |

The tests are deliberately **rule-oriented**: they assert that the *playbook rules we
encoded* behave correctly (e.g. "3.4 GPA is below threshold"), not just that the code
runs. That makes the test suite double as executable documentation of which playbook
rules are implemented.

Run them with:

```bash
uv run pytest -q
```

---

## 8. Why this shape sets up the rest of the project

Phase 0 is intentionally "boring infrastructure," and that mirrors the playbook's own
advice (Chapter 7: do the unglamorous preparation first; applying is the *finish*
line). Concretely, it leaves Phase 1 with everything it needs:

- **A validated profile to read from** — the Resume Builder consumes
  `verified_achievements()` and gets honesty enforced for free.
- **A grounded prompt source** — `PLAYBOOK.as_prompt(AgentSkill.RESUME_BUILDER)`
  yields the Ch. 1–2 principles to drop into the skill's system prompt.
- **Realistic data to build and eval against** — the synthetic fixture, complete with
  intentional gaps for the skill to detect.

Nothing in Phase 1 has to re-derive what a good bullet is, where the data lives, or
what the playbook says — Phase 0 already made those first-class.

---

## Appendix: glossary

- **ATS (Applicant Tracking System):** software companies use to store and screen
  resumes, often with keyword/format heuristics before any human reads them. Several
  Ch. 2 rules (PDF only, no tables, acronym expansion) exist to survive it.
- **Pydantic model:** a Python class describing a data shape; instantiating it
  validates and coerces the input, and it can serialize to/from JSON.
- **Fixture:** a fixed, known piece of data used to develop or test against — here,
  the synthetic sample profile.
- **`src/` layout:** packaging convention where importable code lives under `src/`,
  forcing tests to run against the installed package.
- **Editable install:** installing a package so that source edits take effect
  immediately without reinstalling; `uv sync` sets this up for the local package.
