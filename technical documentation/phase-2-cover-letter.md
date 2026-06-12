# Phase 2 — Cover Letter / Outbound Email Writer + Company Research

**Status:** Complete · **Scope:** Chapter 3 — draft a cover letter (or its modern
equivalent, an outbound prospecting email) that *does no harm*, plus the **Company
Research** capability that feeds the one paragraph that matters.

This document covers what Phase 2 built, the architecture, and the reasoning. It
assumes Phase 0 (profile store, playbook loader) and reuses the Phase 1 pattern of
splitting deterministic checks from LLM generation — see `phase-1-resume-builder.md`.

---

## 1. The Chapter 3 thesis, and how it shapes the design

Chapter 3's stance is deliberately humble: **you can't win a job with a cover letter,
but you can lose one.** Its job is defense — "first, do no harm." The things that get
a letter rejected are mechanical (a typo, the wrong company name, "Dear Hiring
Manager", no customization), and the *one* thing that helps is paragraph 3 — "why
you, specifically" — which proves you actually researched the company.

That splits the work cleanly, the same way Chapter 2 did:

```
                       ┌──────────────────────┐
   CompanyResearch ───▶│  Cover letter writer │──▶ CoverLetter ──┐
   profile, job    ───▶│   (LLM, optional)    │   (structured)   │
                       └──────────────────────┘                  ▼
                       ┌──────────────────────┐          ┌──────────────┐
   CoverLetter     ───▶│  Cover letter linter │────────▶ │ FindingsReport│
   + company/referral  │   (deterministic)    │          │ (chapter-cited)│
                       └──────────────────────┘          └──────────────┘
```

- The **deterministic linter** catches every downside risk the chapter lists. No
  model, so it's instant, free, and fully tested.
- The **LLM writer** does the one creative thing — composing four good paragraphs —
  and is the only component that needs an API key.
- **Company Research** is its own capability because paragraph 3 depends on it, and
  because later skills (networking, interview prep) will want the same company facts.

---

## 2. A shared findings model (`findings.py`)

Phase 1's linter had a `Severity` enum and a `Finding` model (a chapter-cited issue).
Phase 2 needs the exact same shape for cover-letter issues, and Phases 4+ will too.
So those types were lifted into a new top-level `findings.py`:

- `Severity` — `ERROR` (gets you rejected) / `WARNING` (fix before sending) / `INFO`.
- `Finding` — `code`, `severity`, `message`, **`chapter`** (the playbook traceability),
  and an optional `where`.
- `FindingsReport` — a list of findings with `errors`, `warnings`, `has_errors`, and
  `by_code()` accessors.

The resume linter's `LintReport` now simply subclasses `FindingsReport`, so nothing
about Phase 1 changed behaviorally — the refactor is pure de-duplication, and the
existing tests passed unchanged. This is the standard "rule of three" move: once a
concept appears in a third place, give it a home.

---

## 3. Company Research (`research/company.py`)

Paragraph 3 needs *specific, true* facts about the company. The data model captures
both the fact and its provenance:

- **`CompanyFact`** — `text`, a `FactCategory` (product launch / CEO statement / news
  / market / industry challenge), and `source` / `url` / `date`. Provenance matters
  because the candidate must be able to verify a claim before sending, and because a
  wrong fact in a cover letter is exactly what gets it rejected.
- **`CompanyResearch`** — the company name, the hiring manager's name/title, and a
  list of facts, with `has_specifics` and `best_fact()` helpers.

### The provider seam (why research is an interface, not a function)

How research is *obtained* is deliberately abstracted behind a `ResearchProvider`
Protocol with one method, `research(company) -> CompanyResearch`. The only
implementation today is **`ManualResearchProvider`**: you supply the facts, it stores
them keyed by company name (case-insensitive), and a lookup for an unknown company
**raises `KeyError` rather than inventing anything**.

This was a deliberate choice over two alternatives:

- *LLM-from-memory* (ask the model what it knows about the company) — rejected. It
  hallucinates and goes stale, and the whole point of paragraph 3 is that the detail
  is real and current.
- *Live web lookup now* — deferred. It adds an external dependency and non-determinism
  to the phase. Because access goes through the Protocol, a live-web provider can be
  added later as a drop-in implementation without touching the writer or the linter.

So Phase 2 stays offline and honest by construction, while leaving the upgrade path
open.

---

## 4. The cover letter model (`coverletter/models.py`)

A `CoverLetter` is `format` (`LETTER` or `EMAIL`), an optional `subject` (email only),
a `salutation`, a list of `paragraphs`, and a `signoff`, with `body_text()` /
`full_text()` renderers.

One model serves both outputs because the playbook is explicit that **"your outbound
email is your cover letter"** — the four-paragraph principles are identical, the email
just adds a subject line and a lighter register. Representing them as one type with a
`format` flag avoids duplicating all the structure and all the linting.

---

## 5. The "do no harm" linter (`coverletter/linter.py`)

`lint_cover_letter(letter, *, company, referral=None, research=None)` returns a
`FindingsReport`. Each check maps to a specific Chapter 3 rule:

| Finding code | Severity | Rule |
|---|---|---|
| `generic_salutation` | warning | "Dear Hiring Manager" etc. — ~30% more likely to be rejected. If a name is known, the message names it. |
| `missing_company_name` | **error** | The target company name doesn't appear in the letter — a wrong/missing name is an instant reject. |
| `placeholder_text` | **error** | Leftover `[Company]` / `TODO` template placeholders. |
| `not_four_paragraphs` | warning | The structure isn't the prescribed four paragraphs. |
| `no_company_research` | warning | No research available, so P3 can't be specific. |
| `p3_not_specific` | warning | Research exists but P3 doesn't echo the company name or any researched fact. |
| `referral_not_in_first_sentence` | warning | A referral was provided but isn't named in sentence one. |
| `too_long` | warning | Over a one-page word budget — more length, more chances to err. |

The interesting check is `p3_not_specific`: it confirms paragraph 3 actually *uses*
the research by testing whether the company name or a meaningful word (>4 letters)
from any researched fact appears in that paragraph. This catches the most common
failure — a letter that claims to be customized but is actually generic.

---

## 6. The LLM writer (`coverletter/writer.py`)

`CoverLetterWriter.write(profile, *, company, role, ...)` produces a structured
`CoverLetter` via `claude-opus-4-8` and `messages.parse`. It follows the same two
testability seams as the Phase 1 rewriter:

1. **`build_cover_letter_prompt(...)` is a pure function** — the (system, user) prompt
   is assembled with no I/O, so the grounding is unit-tested directly. The system
   prompt is `PLAYBOOK.as_prompt(AgentSkill.COVER_LETTER)` plus an explicit honesty
   ruleset; the user message carries the candidate brief (verified achievements only),
   the role/company, any referral, the job description, and the research facts —
   clearly labelled as "the ONLY source for company-specific claims".
2. **The Anthropic client is injected**, defaulting to `anthropic.Anthropic()` lazily,
   so tests pass a fake and never need a key.

### Honesty, again enforced in layers

As in Phase 1, "never fabricate" is structural rather than hoped-for:

- The prompt only ever includes the candidate's **verified** achievements.
- The system prompt forbids inventing company facts (P3 may use *only* the supplied
  research; with no research, P3 stays general rather than invented) and forbids
  claiming experience not in the profile.
- It also encodes the salutation rule: address the real hiring manager by name, and
  if none is known, address the specific team/role — never "Dear Hiring Manager".
- The deterministic linter then independently re-checks the *output* for the same
  failures, so a slip by the model is still caught before sending.

---

## 7. Testing

69 tests total, all offline. The Phase 2 additions:

| File | Covers |
|---|---|
| `test_research.py` | `has_specifics` / `best_fact`; case-insensitive manual lookup; the Protocol is satisfied; unknown-company lookup raises rather than inventing. |
| `test_coverletter_linter.py` | A clean letter passes; each finding fires on the right defect (generic salutation with name suggestion, missing company name, placeholders, wrong paragraph count, non-specific P3, missing/poorly-placed referral, over-length). |
| `test_coverletter_writer.py` | Prompt grounding (Chapter 3, honesty rules, research + hiring-manager passthrough); verified-only achievements; the no-research warning; the email subject-line request; the model is called with the right schema; the requested format is recorded; email rendering. |

Run with `uv run pytest -q`.

---

## 8. What's deferred (and why)

- **A live-web `ResearchProvider`.** The Protocol and the manual provider are in
  place; a provider that pulls recent launches/news via web search slots in behind
  the same interface when wanted. Deferred to keep Phase 2 deterministic and
  hallucination-free.
- **Typo detection** remains a shared follow-up (noted in Phase 1) — it belongs to the
  LLM's read-through rather than a noisy dictionary check, and applies equally to
  letters.

---

## Appendix: glossary

- **Provider / Protocol:** an interface (here `ResearchProvider`) defining a method
  any implementation must offer, so the concrete source of company facts can be
  swapped (manual now, web later) without changing callers.
- **Provenance:** the source/URL/date attached to a fact so it can be verified — the
  guard against citing something false or stale in paragraph 3.
- **`messages.parse`:** the Anthropic SDK call that constrains the model's response to
  a Pydantic schema and returns a validated object, not free text.
- **Rule of three:** the refactoring heuristic that a concept earns a shared home once
  it appears in a third place — why `Finding` moved to `findings.py`.
