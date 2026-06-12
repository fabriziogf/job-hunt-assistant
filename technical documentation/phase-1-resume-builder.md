# Phase 1 — Resume Builder

**Status:** Core complete · **Scope:** the highest-leverage skill — turn a verified
profile into a Chapter 2-compliant resume. Three pieces: a deterministic **linter**,
an LLM **X/Y/Z rewriter**, and an **assembler** that ties them together.

This document covers what Phase 1 built, the architecture, and the reasoning behind
the choices. It assumes Phase 0 (the profile store and playbook loader) — see
`phase-0-foundations.md`.

---

## 1. The central design decision: split deterministic rules from LLM judgement

Chapter 2 of the playbook is a mix of two very different kinds of rules:

- **Mechanical rules** — "GPA below 3.5? leave it off", "one page per decade", "every
  bullet needs a number", "never include unverified claims". These are pure logic.
- **Judgement calls** — rewriting "Managed sorority budget" into a crisp, quantified
  X/Y/Z bullet in the candidate's voice. This needs a language model.

The whole phase is organized around keeping these two separate:

```
                 ┌─────────────────┐
   profile ─────▶│  Resume linter  │── findings (chapter-cited) ──┐
                 │ (deterministic) │                              │
                 └─────────────────┘                              ▼
                 ┌─────────────────┐                       ┌─────────────┐
   profile ─────▶│   Assembler     │── selects/orders ────▶│   Resume    │
   (+ JD)        │ (deterministic) │   + calls rewriter    │ (structured)│
                 └────────┬────────┘                       └─────────────┘
                          │ optional
                          ▼
                 ┌─────────────────┐
                 │  X/Y/Z rewriter │  (LLM — claude-opus-4-8)
                 └─────────────────┘
```

**Why split them?** Three concrete payoffs:

1. **Tests need no API key.** The deterministic parts (linter, selection, ordering,
   trimming, GPA filtering) are ~80% of the value and are fully unit-tested offline.
   The one component that *must* call a model is isolated behind an interface that
   tests fake out. All 41 tests run with no network and no key.
2. **Speed and cost.** Rejecting a resume for a sub-3.5 GPA or a missing email
   shouldn't cost a model call. The linter runs instantly and free.
3. **The honesty rule gets two independent enforcement points** (see §5).

---

## 2. The resume linter (`resume/linter.py`)

A pure function `lint_profile(profile) -> LintReport`. It inspects the profile and
emits a list of **`Finding`** objects, each carrying a `code`, a `Severity`
(`ERROR` / `WARNING` / `INFO`), a human-readable message, and — importantly — the
**chapter number** it comes from, so every piece of advice is traceable to the
playbook.

What it checks, all from Chapter 2 (plus Chapter 3's "first, do no harm" mindset):

| Finding code | Severity | Rule |
|---|---|---|
| `missing_metric` | warning | A verified achievement has no measurable result (Y). |
| `gpa_below_threshold` | warning | A GPA under 3.5 should be omitted. |
| `award_lacks_context` | info | An award name too short to say what it was *for*. |
| `likely_too_long` | warning | Bullet count exceeds the one-page-per-decade budget. |
| `missing_email` | **error** | No email — a recruiter literally can't reach the candidate. |
| `missing_phone` | info | No phone number. |
| `unverified_excluded` | info | N achievements are held back until a human verifies them. |
| `brands_available` | info | Recognizable brand names the resume should surface. |

Two helper concepts worth calling out:

- **Length budget.** `recommended_max_pages()` computes pages from the span between
  the earliest role and a reference date (`as_of`, injectable so tests are
  deterministic), at one page per decade. The linter multiplies that by a
  bullets-per-page heuristic to decide if the resume likely overflows.
- **`LintReport`** exposes `errors`, `warnings`, `has_errors`, and `by_code()` so
  callers (and tests) can query results without re-filtering by hand.

"Severity" maps to the playbook's own emphasis: an `ERROR` is something the guide
says *actively gets you rejected*; a `WARNING` is a rule violation to fix; `INFO` is
an opportunity (like brands to name-drop).

---

## 3. The X/Y/Z rewriter (`resume/rewriter.py`)

This is the only component that calls a model. It rewrites one verified
`Achievement` into a polished bullet following Chapter 2's formula —
"Accomplished [X] as measured by [Y] by doing [Z]" — optionally tailored to a target
job description.

### Structured output, not free text

The rewrite comes back as a validated **`BulletRewrite`** Pydantic model
(`rewritten`, `has_metric`, `notes`), using the Anthropic SDK's
`client.messages.parse(..., output_format=BulletRewrite)`. The SDK validates the
model's JSON against the schema for us — no brittle string parsing, and a malformed
response fails loudly rather than silently.

The model used is `claude-opus-4-8`.

### Two design seams that make it testable

1. **Prompt construction is a pure function.** `build_rewrite_prompt(achievement,
   job_description)` returns the `(system, user)` strings with no I/O. The system
   prompt is assembled from `PLAYBOOK.as_prompt(AgentSkill.RESUME_BUILDER)` (the
   Chapter 1–2 principles from Phase 0) plus an explicit honesty ruleset. Tests
   assert the grounding is present (the X/Y/Z formula, the no-fabrication rule, the
   job description) without calling anything.
2. **The client is injected.** `ResumeRewriter(client=...)` takes any object exposing
   `.messages.parse(...)`. Tests pass a fake that records the call and returns a
   canned `BulletRewrite`. In production the client defaults to
   `anthropic.Anthropic()`, which reads `ANTHROPIC_API_KEY` from the environment —
   constructed lazily, so importing the module never requires a key.

---

## 4. The assembler (`resume/assembler.py`)

`build_resume(profile, *, job_description=None, rewriter=None, as_of=None) -> Resume`
is the orchestrator. It produces a structured, validated **`Resume`** (with
`ResumeExperience`, `ResumeEducation`, `ResumeBullet` sub-models) plus a Markdown
renderer.

Its logic — all deterministic — applies the Chapter 2 rules that govern *which*
content makes the cut and in *what order*:

1. **Lint first**, and attach the findings to the `Resume` so the user sees what to
   fix alongside the output.
2. **Select** only verified achievements (honesty gate).
3. **Order** experiences most-recent-first (current roles ahead of past ones); within
   each role, quantified bullets come before unquantified ones.
4. **Trim** to the one-page-per-decade budget, dropping the weakest/oldest bullets
   once the budget is spent.
5. **Filter education**: a GPA is carried into the output only if it clears the 3.5
   threshold; otherwise it's dropped (the entry stays, the number goes).
6. **Render** each kept achievement into a bullet.

### The optional-rewriter seam

Step 6 is where the LLM plugs in. If a `rewriter` is passed, each bullet is polished
by the model; if not, the assembler falls back to the deterministic
`Achievement.to_xyz_bullet()` from Phase 0. This means:

- A complete resume can be assembled — and the whole pipeline tested — **with no API
  key**. The fallback produces a serviceable (if clunky) bullet.
- Upgrading to LLM-quality bullets is a one-argument change, not a rewrite.

This mirrors the rewriter's own injection seam: the expensive/external dependency is
always optional and always fakeable.

---

## 5. How "never fabricate" is enforced — defense in depth

The project's hard rule is *never invent candidate data*. Phase 1 enforces it at
**three** independent layers, so no single bug can produce a fabricated resume:

1. **The profile** (Phase 0) only treats `verified=True` achievements as usable.
2. **The assembler** selects exclusively from verified achievements — unverified ones
   never reach the rewriter or the output.
3. **The rewriter** refuses an unverified achievement outright (`ValueError`), and its
   system prompt forbids inventing metrics/employers/outcomes. If an achievement has
   no metric, the model must keep the bullet qualitative and report
   `has_metric=False` — never manufacture a number.

The linter reinforces this by surfacing how many achievements are being *held back*
for lack of verification (`unverified_excluded`), turning the honesty constraint into
visible, actionable feedback rather than a silent omission.

---

## 6. Testing

41 tests total, all offline. The Phase 1 additions:

| File | Covers |
|---|---|
| `test_resume_linter.py` | Each finding fires on the right input; the sample fixture's known gaps (one missing metric, one sub-3.5 GPA); the page budget; missing-email as an error; chapter citations present. |
| `test_resume_rewriter.py` | Prompt grounding (X/Y/Z formula, honesty rules, JD inclusion, missing-metric handling); the model is called with the right schema; unverified achievements are refused; batch rewrite skips unverified. |
| `test_resume_assembler.py` | Verified-only selection; recency ordering; quantified-first; GPA filtering; "Present" for current roles; the length-budget trim; findings attached; Markdown rendering; the injected-rewriter seam. |

The tests are deliberately **rule-oriented** — they assert the playbook rules behave
correctly (e.g. "40 bullets trim to 14 on a one-page budget"), so the suite doubles
as a checklist of which Chapter 2 rules are implemented.

Run them with `uv run pytest -q`.

---

## 7. What's deferred (and why)

Phase 1's *core* is done; two Chapter 2 items are intentionally left for follow-ups:

- **PDF rendering** with the hard formatting rules (PDF-only, 11pt, ½" margins, no
  tables/columns, contact info on every page). The structured `Resume` model and its
  Markdown renderer are the foundation; a PDF backend slots in next without touching
  the assembly logic. Deferred to keep a PDF dependency out until the content layer
  is settled.
- **Typo detection.** The playbook treats typos as a hard reject filter, but naive
  spell-checking is noisy on names, brands, and acronyms. This belongs to the LLM
  rewriter's judgement (it reads every bullet anyway) rather than a dictionary check,
  and will be wired in as an explicit pass.
- **The ATS Optimizer** (also Chapter 2 — keyword-match scoring against a job
  description) is its own skill in the plan and reuses the rewriter's JD-tailoring
  groundwork.

---

## Appendix: glossary

- **Linter:** a tool that inspects something and reports rule violations — here,
  resume rule violations rather than code style.
- **Finding / Severity:** one reported issue, tagged error/warning/info by how much
  the playbook says it matters.
- **Structured output:** constraining the model's response to a fixed JSON schema
  (via `messages.parse`) so it returns validated data, not free text.
- **Dependency injection:** passing a component (the Anthropic client, the rewriter)
  in from outside rather than constructing it internally — what lets tests substitute
  a fake and run offline.
- **`as_of`:** an injectable "today" date, so length/recency calculations are
  deterministic in tests instead of depending on the wall clock.
