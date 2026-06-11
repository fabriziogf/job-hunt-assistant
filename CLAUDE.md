# Job Hunt Assistant

An AI agent that helps a candidate run a full job search end-to-end, built on the
principles in `guide.pdf` — Laszlo Bock's *Apply Within: The Full Playbook* (former
SVP of People Operations at Google). The guide is a 112-page, 8-chapter playbook
distilled from reviewing 30M+ resumes and 100K+ applicants at Google.

## Source material

`guide.pdf` is the single source of truth for the agent's behavior. Every skill below
maps to a chapter, so the agent gives advice grounded in the playbook rather than
generic LLM intuition.

| Ch | Topic | Core principle |
|----|-------|----------------|
| 1 | Hiring is rigged | You don't need to be the best — you need to know the game. |
| 2 | Resume in one formula | "Accomplished [X] as measured by [Y] by doing [Z]." |
| 3 | The cover letter trap | First, do no harm. Outbound email is the modern cover letter. |
| 4 | Networking without a network | Referrals get hired 5–10x more often. Ask for advice, not a job. |
| 5 | The interview secret | People hire people they like. Get them to love you. |
| 6 | Practice or perish | 30 questions × 2 answers × 3 reps ≈ 13.5 hours. |
| 7 | Land the interview, last | B-tier companies first; volume game (~100 apps → ~1 offer). |
| 8 | Negotiate or lose | Max leverage is the moment of the offer. Always ask. |

## Planned skills

The agent is a set of focused skills sharing one **candidate profile store** (the
single source of truth for experience, metrics, and achievements) and a **company
research** capability that feeds several skills.

1. **Resume Builder** (Ch. 2) — rewrite bullets into X/Y/Z; enforce formatting rules
   (PDF, 11pt, ½" margins, no tables/columns, contact info per page); 1 page/decade;
   typo hunt; brand name-dropping; GPA/awards/hardship logic; lie detection.
2. **ATS Optimizer** (Ch. 2) — mirror job-description phrasing, spell out acronyms
   once, score keyword match (target 75%+).
3. **Cover Letter / Outbound Email Writer** (Ch. 3) — 4-paragraph structure with a
   research-driven "why you, specifically" paragraph; real hiring-manager name;
   per-job customization; company-name + typo guard.
4. **Networking & Referral Assistant** (Ch. 4) — map connection-to-a-connection
   paths; "ask for advice" reframing; manufacture-a-coincidence outreach; the 5
   advice questions; follow-up etiquette.
5. **Interview Prep Coach** (Ch. 5 & 6) — generate ~30 likely questions; 2 answers
   each, 3 reps; universal answer structure (restate → preview → story → summarize);
   "get them to love you" coaching; post-interview log + self-scoring.
6. **Application Pipeline Tracker** (Ch. 7) — 6-column tracker; volume math;
   B-tier-first sequencing; follow-up cadence (every 2 weeks for 6 weeks).
7. **Offer Negotiation Advisor** (Ch. 8) — market-rate research; ask vs. walk-away
   numbers; deflection scripts; multi-lever asks beyond base; get-it-in-writing.

Cross-cutting: **candidate profile store**, **company research**, **job
discovery/matching** (extends beyond the literal guide).

## Development plan

- **Phase 0 — Foundations:** project scaffold, candidate profile schema, a shared
  loader that extracts the relevant playbook principles per skill.
- **Phase 1 — Resume Builder + ATS Optimizer:** highest leverage; the resume "does
  the actual work." Ship these first.
- **Phase 2 — Cover Letter / Outbound Email + Company Research.**
- **Phase 3 — Interview Prep Coach** (question generation, answer structuring,
  practice loop).
- **Phase 4 — Networking, Pipeline Tracker, Negotiation Advisor.**
- **Phase 5 — Job discovery/matching + orchestration** tying skills into one flow.

Each phase ships an independently useful skill with its own eval before moving on.

## Conventions

- Stack follows the personal vibe-coding setup: Python 3.12 via `uv`, Anthropic SDK
  for agent/tool-use, Claude Code as the build environment. Keep the stack small.
- Never fabricate candidate data. The guide is emphatic: don't lie, don't stretch.
- Ground advice in `guide.pdf` chapters; cite the principle being applied.
