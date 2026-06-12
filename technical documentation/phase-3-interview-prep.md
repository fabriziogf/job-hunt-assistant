# Phase 3 — Interview Prep Coach

**Status:** Complete · **Scope:** Chapters 5 & 6 — turn a candidate into a prepared
interviewee: a predicted question bank, two structured answers per question drawn
from real achievements, the practice-hours math, "get them to love you" coaching,
and a post-interview self-scoring loop.

This document covers what Phase 3 built and why. It assumes Phase 0 (profile store,
playbook loader) and continues the now-standard pattern: a large deterministic core
plus a thin, injected LLM layer (see `phase-1-resume-builder.md`).

---

## 1. Two chapters, one skill

Phase 3 spans two playbook chapters that work together:

- **Chapter 6 ("Practice or perish")** is mechanical: interviews are nearly
  identical, so predict the questions, prepare two answers each in a fixed
  structure, and do the reps. It even gives the arithmetic — 30 questions × 2
  answers × 3 reps ≈ 13.5 hours.
- **Chapter 5 ("The interview secret")** is behavioral: your real goal is to get the
  interviewer to *like* you. It's a set of concrete do's and don'ts.

Because so much of this is fixed structure and fixed content, the skill is
**mostly deterministic**. The model is only needed for the two genuinely generative
tasks — inventing role-specific questions, and drafting answers — and both are
isolated behind the same injected-client seam used in Phases 1–2. The result: of the
14 new tests, every one runs offline.

The package breaks into five modules:

```
interview/
├── questions.py   the canonical 12, the QuestionBank, the practice math   (deterministic)
├── answers.py     the four-part Answer model + lint_answer                (deterministic)
├── log.py         post-interview self-scoring                             (deterministic)
├── coaching.py    Chapter 5 "get them to love you" content                (deterministic)
└── generator.py   QuestionGenerator + AnswerCoach                         (LLM)
```

---

## 2. The question bank and the practice math (`questions.py`)

Chapter 6 lists 12 questions you'll "almost certainly be asked." Those are encoded as
structured data — `CANONICAL_QUESTIONS`, each an `InterviewQuestion` with a `text`, a
`QuestionCategory` (motivational / behavioral / self-assessment / logistics /
closing / role-specific), and a `canonical=True` flag. A `QuestionBank` collects them
and reports whether it's reached the ~30-question target.

The most playbook-faithful piece is **`practice_plan()`**, which turns a question
count into the chapter's arithmetic:

- `total_reps = questions × answers_each × reps_each` (defaults 2 and 3).
- `estimated_hours` uses a calibrated **4.5 minutes per spoken rep**, chosen so the
  chapter's own example reconciles exactly: 30 questions → 180 reps → **13.5 hours**.

That number isn't decoration — surfacing "this is 13.5 hours, spread over a week of
evenings" is the chapter's core motivational lever, so it's a first-class output.

---

## 3. The four-part answer (`answers.py`)

Chapter 6's universal answer structure is: **restate → preview → story → summarize**
("tell them what you'll say, say it, tell them what you said"). Rather than store an
answer as free text and try to detect the structure afterward, the `Answer` model
*is* the structure — four named string fields, plus an `achievement_tag` recording
which verified achievement the story came from (honesty traceability).

`lint_answer()` then checks quality deterministically and emits chapter-cited
findings (reusing the shared `FindingsReport` from Phase 2):

- a `missing_<part>` warning for any of the four parts left empty;
- `story_not_quantified` (info) when the story contains no numbers — Chapter 6 says
  "specific, with numbers when possible";
- `story_too_thin` / `story_too_long` (info) for stories outside a sensible word band.

An `AnswerSet` bundles the **two** answers per question that Chapter 6 prescribes, so
that a second interviewer who repeats a question gets the fresh, second answer.

---

## 4. The post-interview log (`log.py`)

Chapter 6's "keep the list alive": within 30 minutes of every interview, log every
question, score yourself out of 10, add what you didn't predict, and rewrite your
weakest answers. `InterviewLog` models exactly that debrief:

- `AnsweredQuestion` carries a `question`, a validated 0–10 `score`, and `notes`;
- `average_score`, `weakest(n)`, `answers_to_rewrite()` (everything at or below a
  weak-score threshold), and `questions_to_add()` turn the log into a concrete
  next-actions list.

This closes the loop: the questions surfaced in one interview feed back into the
question bank for the next one.

---

## 5. The "get them to love you" coaching (`coaching.py`)

Chapter 5 is advice, not generation, so it's exposed as **structured, deterministic
data** rather than run through a model:

- `COACHING_POINTS` — the behaviors that win (everyone is your interviewer, small
  talk is the best talk, reframe missing experience, dress so nobody notices, treat
  an AI interviewer like a real one, thank-you within 24h, a near-miss is a
  relationship);
- `CLOSING_QUESTIONS` — the three strong answers to "do you have any questions for
  me?";
- `INSTANT_REJECTIONS` — the five things that instantly sink you.

Keeping this as data (not a prompt) means it's stable, citable, testable, and free —
and it can still be dropped into any prompt later if a generative surface wants it.

---

## 6. The LLM generators (`generator.py`)

Only two tasks need a model, and both follow the established seams — a **pure prompt
builder** plus an **injected Anthropic client** (`claude-opus-4-8`, `messages.parse`
for validated structured output):

**`QuestionGenerator`** expands the canonical 12 toward the ~30 target by asking the
model only for the *shortfall* of role-specific questions (it computes
`target - canonical_count` and requests exactly that many), then appends them to a
bank seeded with the canonical set. If the target is already met, it makes no model
call at all.

**`AnswerCoach`** drafts the two four-part answers for a question. Its honesty
contract is the strict part: the prompt supplies **only the candidate's verified
achievements** as allowable story material, and the system rules forbid inventing
metrics, employers, projects, or outcomes — every story must trace to a real
achievement (recorded in `achievement_tag`). This is the same defense-in-depth as the
resume rewriter and cover-letter writer: verified-only input, explicit
no-fabrication rules, and a deterministic `lint_answer()` available to re-check the
output.

Both are grounded via `PLAYBOOK.as_prompt(AgentSkill.INTERVIEW_PREP)`, which supplies
the Chapter 5 & 6 principles.

---

## 7. Testing

83 tests total, all offline. The Phase 3 additions:

| File | Covers |
|---|---|
| `test_interview_core.py` | The canonical 12; bank categories and target; the practice math reconciling to 180 reps / 13.5 hours; the answer linter (complete answer passes, missing parts flagged, unquantified story flagged); the log (average, weakest, rewrite list, new questions, score-range validation); the coaching surfaces the Chapter 5 essentials. |
| `test_interview_generator.py` | Question prompt grounding; generation appends to canonical and requests exactly the shortfall; no model call when the target is already met; the answer prompt uses verified achievements only; the coach calls the model with the right schema and records the question. |

Run with `uv run pytest -q`.

---

## 8. What's deferred (and why)

- **A thank-you-note drafter.** Chapter 5 stresses a thank-you within 24 hours
  referencing one specific thing each interviewer said. It's a natural small LLM
  surface that reuses the cover-letter writer's shape, deferred to keep this phase
  focused on the core prep loop.
- **Mock-interview orchestration.** Chaining the generators into a live
  question-by-question practice session (ask → draft → score) is an orchestration
  concern that belongs with Phase 5, not the skill itself.
- **Typo detection** remains the shared follow-up noted since Phase 1.

---

## Appendix: glossary

- **Canonical question:** one of the 12 questions Chapter 6 says you'll almost
  certainly be asked — stored as fixed data, the seed for every question bank.
- **Four-part structure:** the restate → preview → story → summarize shape every
  answer follows; modeled as fields so it can't be "missed".
- **Rep:** one spoken-aloud practice of one answer; the unit the practice math counts
  (180 of them ≈ 13.5 hours).
- **`achievement_tag`:** the field linking an answer's story back to the verified
  achievement it came from — the honesty audit trail for generated answers.
