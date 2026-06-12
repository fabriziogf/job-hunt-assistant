# Phase 5 — Job Discovery + Orchestration (the capstone)

**Status:** Complete · **Scope:** the final phase — find the right jobs (job
discovery/matching, which extends beyond the literal playbook) and tie the seven
skills into one end-to-end flow (orchestration).

This document covers Phase 5 and, because it's the capstone, how the whole system
fits together. It assumes Phases 0–4.

---

## 1. What was missing before Phase 5

After Phase 4 all seven skills existed, but as **independent tools**. A user still
had to: pick a job, run the resume builder, run the ATS scorer, run the cover-letter
writer, run the interview prep, and remember to log it in the pipeline — wiring the
outputs of each into the next by hand.

Phase 5 closes that gap with two additions:

1. **Discovery** — the guide assumes you already have jobs to apply to; this adds the
   step of finding the right ones and ranking them by fit.
2. **Orchestration** — a single coordinator that takes one job posting and runs the
   relevant skills in order, producing one consolidated application package.

---

## 2. Job discovery & matching (`discovery/match.py`)

A `JobPosting` is a company, role, description, optional location/URL, and the
candidate's own A/B/C `tier` (dream / middle / fallback — reused from the pipeline).

The matcher reuses earlier phases rather than inventing new scoring:

```
match_job(profile, job):
    resume = build_resume(profile)          # Phase 1, deterministic
    report = score_resume(resume, job.description)   # Phase 1 ATS
    -> JobMatch(score, matched_keywords, missing_keywords)
```

So a job's fit score *is* the ATS keyword match between the candidate's assembled
resume and the posting — which means the same signal that tells you "this is a good
job to pursue" also tells the resume and cover letter which keywords to address.
`rank_jobs()` orders postings best-fit first, and `JobMatch.recommended` flags those
clearing the Chapter 2 75% target.

Postings are supplied manually for now, deliberately mirroring the company-research
design from Phase 2: a live-scraping source can implement the same shape later
without touching the matcher.

---

## 3. The orchestrator (`orchestration/orchestrator.py`)

`ApplicationOrchestrator` holds the candidate profile (and any injected components),
and `prepare(job)` produces an **`ApplicationPackage`**:

```
ApplicationPackage:
  job            : JobPosting
  resume         : Resume          (Phase 1, tailored to the job)
  ats            : ATSReport       (Phase 1, scored against the posting)
  question_bank  : QuestionBank    (Phase 3)
  cover_letter   : CoverLetter | None   (Phase 2)
```

The control flow inside `prepare()`:

1. **Phase 1** — `build_resume(profile, job_description=..., rewriter=...)` then
   `score_resume()`. Always runs.
2. **Phase 2** — only if a cover-letter writer is injected. Company research is
   resolved through the `ResearchProvider` seam (an explicitly-passed `research`
   wins; otherwise the provider is queried; a missing entry falls back to `None` so
   the letter stays general rather than crashing or inventing).
3. **Phase 3** — a question bank: the injected generator's ~30 tailored questions, or
   the canonical 12 by default.
4. **Phase 4 hand-off** — `to_application(job)` emits a pipeline `Application` record.

### The one design decision that makes this testable: deterministic by default

The orchestrator never constructs an LLM client itself. Every generative component is
**injected and optional**:

- with nothing injected, `prepare()` runs **fully offline** — a deterministic resume,
  a real ATS score, the canonical question bank, no cover letter — and still returns a
  usable package;
- inject the rewriter / cover-letter writer / question generator, and each step
  upgrades to model quality with no change to the calling code.

This is the same seam used in every prior phase, applied one level up: the whole
pipeline is exercised in tests with fakes, no API key, and the production path is the
identical code with real writers passed in.

---

## 4. How the whole system fits together

With Phase 5 in place, the data flows in one direction and the chapters interlock
exactly as the playbook intends:

```
        profile (verified facts)            company research
              │                                    │
              ▼                                     ▼
   rank_jobs ─▶ JobPosting ─▶ ApplicationOrchestrator.prepare ──────────┐
                                  │  resume (Ch.2) ──▶ ATS score (Ch.2)  │
                                  │  cover letter (Ch.3) ◀── research    │
                                  │  question bank (Ch.5/6)              │
                                  └──────────────┬──────────────────────┘
                                                 ▼
                                   to_application ─▶ Pipeline (Ch.7)
                                                          │
                                          offer ──▶ Negotiation (Ch.8)
```

The single source of truth (the verified profile) feeds everything; company research
flows into the cover letter; the B-tier-first pipeline produces the offer that arms
the negotiator's "get two offers" leverage. The orchestrator makes that flow one
method call instead of seven manual steps.

---

## 5. Honesty, end to end

The capstone inherits the layered "never fabricate" enforcement of every phase
without adding a new hole: the orchestrator only ever passes the **verified** profile
and **resolved** (never invented) research into the writers, and the deterministic
linters from each skill remain available to re-check any generated surface. Discovery
adds no generation at all — a fit score is pure keyword math — so there's nothing new
to fabricate.

---

## 6. Testing

116 tests total, all offline. The Phase 5 additions:

| File | Covers |
|---|---|
| `test_discovery.py` | `match_job` scores against a posting; `rank_jobs` orders best-fit first (a PM role beats a chef role for an AI/ML profile); the `recommended` flag tracks the 75% target; postings default to B-tier. |
| `test_orchestration.py` | `prepare()` runs fully offline by default (resume + ATS + canonical 12, no cover letter); `to_application()` hands off to the pipeline; an injected cover-letter writer receives the provider-resolved research; an injected question generator yields ~30 questions; a missing-research company doesn't crash. |

Run with `uv run pytest -q`.

---

## 7. Where the project stands

All five phases and all seven planned skills are complete:

| Phase | Skill(s) | Chapters |
|---|---|---|
| 0 | Foundations (profile store, playbook loader) | — |
| 1 | Resume Builder + ATS Optimizer | 2 |
| 2 | Cover Letter / Outbound Email + Company Research | 3 |
| 3 | Interview Prep Coach | 5 & 6 |
| 4 | Networking + Pipeline Tracker + Negotiation | 4, 7, 8 |
| 5 | Job discovery + orchestration | — |

### Natural next steps (beyond the plan)

- **A live `ResearchProvider` and a live job source** — both seams exist; wiring them
  to web search turns the offline system into a live one.
- **PDF rendering and a typo pass** — the two Chapter 2 polish items deferred since
  Phase 1.
- **A CLI or thin UI** over `ApplicationOrchestrator` — the orchestrator is already
  the single entry point; a front end is now mostly presentation.
- **Persistence** — every model is JSON-able Pydantic, so saving a pipeline or a
  package to disk is a small step.

---

## Appendix: glossary

- **Fit score:** the ATS keyword match between the candidate's assembled resume and a
  posting — Phase 5 reuses it as the "should I apply here?" signal.
- **ApplicationPackage:** the single structured object bundling everything produced
  for one job (resume, ATS score, question bank, optional cover letter).
- **Deterministic by default:** the orchestrator composes the no-LLM halves of each
  skill unless a generative component is injected — so the whole flow is testable
  without a key, and the production path is the same code with real writers passed in.
- **Provider seam:** the injected-interface pattern (`ResearchProvider`, and the
  injected writers) that lets an external/expensive dependency be swapped or faked.
