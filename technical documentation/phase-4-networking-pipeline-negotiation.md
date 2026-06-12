# Phase 4 — Networking, Pipeline Tracker, Negotiation

**Status:** Complete · **Scope:** three independently-useful skills bundled into one
phase — the **Networking & Referral Assistant** (Chapter 4), the **Application
Pipeline Tracker** (Chapter 7), and the **Offer Negotiation Advisor** (Chapter 8).

This document covers what Phase 4 built and why. It assumes the patterns established
in Phases 0–3: a deterministic core, an optional injected-LLM layer, chapter-cited
findings, and "never fabricate" enforced structurally.

---

## 1. Why three skills in one phase

Each of these chapters is smaller and more self-contained than the resume or
interview work, and each maps to a tidy mix of *fixed playbook content* (questions,
scripts, ratios, checklists) plus *a little generation*. So rather than three thin
phases, they're bundled — but each ships as its own subpackage with its own tests and
its own commit, so they remain independent.

A useful contrast emerges across the three:

| Skill | Deterministic core | LLM layer |
|---|---|---|
| Networking (Ch. 4) | advice questions, template, etiquette, outreach linter | outreach writer |
| Pipeline (Ch. 7) | tracker, volume math, follow-up cadence, sequencing | **none** |
| Negotiation (Ch. 8) | ask math, compounding cost, plan, scripts, levers | counter-offer writer |

The Pipeline Tracker is the project's first skill with **no model at all** — it's pure
bookkeeping and arithmetic, and a model would add nothing but latency and risk.

---

## 2. Networking & Referral Assistant (`networking/`)

Chapter 4's core move is the reframe: **ask for advice, not a job** — the moment you
ask for a job you become a problem to solve. The skill encodes that.

**`core.py` (deterministic)** holds the chapter's reusable content as data — the five
advice questions, the meeting etiquette, where to find a first connection — plus:

- `outreach_template(...)` — fills the chapter's outreach template (open with a
  genuine coincidence, ask for 15 minutes of advice).
- `lint_outreach(message)` — checks a draft follows the playbook and emits
  chapter-cited findings: `asks_for_job` (the cardinal sin), `generic_opener`
  ("you don't know me, but..."), `no_coincidence` (no "I noticed..." hook),
  `no_advice_ask`, and `too_long`. The job-ask and coincidence checks are regex-based,
  so the most important rule — don't ask for a job — is enforced without a model.

**`writer.py` (LLM)** is `OutreachWriter`: it drafts the advice-ask message, but its
honesty rule is specific to this chapter — it may open **only** with the
candidate-supplied coincidence and must never invent a shared detail (a fabricated
"I loved your talk at X" is worse than no hook at all).

---

## 3. Application Pipeline Tracker (`pipeline/`)

Chapter 7 treats applying as the finish line of a volume game, tracked in a simple
spreadsheet. The whole skill is deterministic.

- **`Application`** is the six-column record (company, role, contact, date applied,
  status, last touch) plus a `CompanyTier`. `Pipeline` aggregates them.
- **Volume math.** `project_funnel(n)` applies the chapter's ratios — 100 → 5 → 1.5 →
  1 — and `applications_needed(target_offers)` inverts it to "~100 applications per
  offer". These make the daunting numbers concrete and honest.
- **Follow-up cadence.** `Application.followup_due(as_of)` encodes "every 2 weeks, for
  6 weeks": due when the application is still open, at least 14 days since the last
  touch, and within 42 days of applying — after which it stops. `should_reapply`
  fires after 90 days of silence.
- **B-tier-first sequencing.** `recommended_application_order()` sorts targets B → A →
  C, because Chapter 7 says to practice on middle-tier companies first and an offer
  there becomes leverage with the A-tier ones (which is exactly what Chapter 8's
  "get two offers" strategy then uses — the chapters interlock).
- The follow-up message and the tactical rules (apply direct, always PDF, multiple
  roles per company) are exposed as data.

Because everything keys off an injectable `as_of` date, all the time-based logic is
deterministic in tests.

---

## 4. Offer Negotiation Advisor (`negotiation/`)

Chapter 8: always negotiate, politely; your maximum leverage is the moment of the
offer; know your four numbers.

**`core.py` (deterministic)**:

- `ask_range(offer)` — the 10–20%-above-offer band.
- `lifetime_value_of_raise(...)` — the compounding "cost of silence". It models a
  raise won today growing with standard annual raises and banked each year at an
  investment return until retirement. With the defaults (40 years, 3% raises, 5%
  return) a $5,000 raise is worth **~$944k** — faithful to the chapter's "$1M+"
  headline, and the single most motivating number in the chapter.
- `build_negotiation_plan(offer, market_low, market_high, walk_away)` — assembles a
  `NegotiationPlan` with the ask band, the standard levers, the deflection scripts,
  and **data-aware notes**: it flags an offer below the market floor (a strong,
  data-backed case), notes when the market supports pushing past the 20% ask, and
  reminds you never to reveal the walk-away number.
- The compensation levers, deflection scripts, and get-it-in-writing checklist are
  data.

**`writer.py` (LLM)** is `CounterOfferWriter`. Chapter 8 is unusually explicit that
you must never lie, so the prompt allows **only** the justifications the candidate
actually supplies (market data, a real competing offer, genuine obligations) and is
told to stay polite and non-greedy — they already chose the candidate.

---

## 5. Honesty, per chapter

The "never fabricate" rule keeps showing up, but Phase 4 is a good illustration that
each chapter has its *own* flavor of dishonesty to guard against, and each writer's
prompt targets that specific one:

- **Networking:** don't invent a shared coincidence.
- **Negotiation:** don't invent leverage (fake competing offers, made-up obligations).
- (Pipeline has no generation, so nothing to fabricate.)

In every case the structural pattern is the same as earlier phases: the prompt is
fed only real, provided inputs, and the deterministic linter (where one exists)
independently re-checks the surface that matters.

---

## 6. Testing

107 tests total, all offline. The Phase 4 additions:

| File | Covers |
|---|---|
| `test_networking.py` | The five advice questions; the template fills and asks for advice; etiquette content; the linter flags job-asking / generic openers / missing coincidence and passes a clean message; the writer grounds in Chapter 4 and passes the coincidence through; the writer calls the model with the right schema. |
| `test_pipeline.py` | Funnel ratios (100→5→1.5→1); ~100 applications per offer; follow-up due after 2 weeks and stopping after 6; closed applications never due; reapply after 3 months; B-tier-first ordering; pipeline status counts and due-follow-up aggregation. |
| `test_negotiation.py` | The 10–20% ask range; the ~$1M compounding figure and its scaling; levers/scripts present; the plan's ask and below-market flagging; the markdown render; the counter-offer prompt grounds and forbids lying; the writer calls the model with the right schema. |

Run with `uv run pytest -q`.

---

## 7. What's deferred (and why)

- **Multi-component compensation modeling.** The negotiation advisor reasons about
  base; modeling base/bonus/equity as separate levers with their own ranges is a
  natural extension, deferred to keep the first cut focused on the headline ask.
- **Persisting the pipeline.** `Pipeline` is an in-memory model with JSON-able
  Pydantic types; wiring it to a real spreadsheet/CSV or a saved file is an
  orchestration concern for Phase 5.
- **Typo detection** remains the shared follow-up noted since Phase 1.

With Phase 4 done, all seven planned skills exist. Phase 5 ties them together
(job discovery + orchestration) — for example, a B-tier offer in the Pipeline Tracker
feeding the Negotiation Advisor's "get two offers" leverage, or company research
flowing from the cover letter into interview prep.

---

## Appendix: glossary

- **Funnel ratios:** the empirical conversion rates from applications to offers
  (~100 → ~1) that turn the volume game into a concrete target.
- **Follow-up cadence:** the every-2-weeks-for-6-weeks rule, encoded as a date
  predicate so "is this due today?" is a pure function of an `as_of` date.
- **Walk-away number:** the lowest offer you'd accept — known to you, never revealed;
  the plan carries it but the scripts never speak it.
- **Compounding cost of silence:** the lifetime value of a raise won at the offer,
  the chapter's argument for why a few minutes of polite asking is worth six figures.
