# Job Hunt Assistant

An AI agent that helps a candidate run a full job search end-to-end — resume,
cover letter, networking, interview prep, application tracking, and offer
negotiation — with advice grounded in a concrete playbook rather than generic
LLM intuition.

## Where the advice comes from

The agent's behavior is based on **Laszlo Bock's _Apply Within: The Full
Playbook_**. Bock was the former SVP of People Operations at Google; the playbook
distills what his team learned from sifting 30M+ resumes and reviewing 100K+
applicants into eight chapters.

> The playbook itself is not redistributed in this repo (it is Bock's copyrighted
> work). Read the original from the author:
> [linkedin.com/in/laszlobock](https://www.linkedin.com/in/laszlobock).

The core reframe: hiring isn't a search for the most qualified person — it's a set
of repeatable, learnable moves. Repeatable moves are exactly what an agent can
help execute well.

## Planned skills

Each skill maps to a chapter of the playbook. All skills share one **candidate
profile store** (the single source of truth for real experience and metrics) and a
**company research** capability.

| Skill | Chapter | What it does |
|-------|---------|--------------|
| **Resume Builder** | 2 | Rewrites bullets into "Accomplished [X] as measured by [Y] by doing [Z]"; enforces formatting rules; typo + honesty checks. |
| **ATS Optimizer** | 2 | Mirrors job-description phrasing, expands acronyms, scores keyword match (target 75%+). |
| **Cover Letter / Email Writer** | 3 | 4-paragraph structure with a research-driven "why you, specifically" paragraph; real hiring-manager name; per-job customization. |
| **Networking Assistant** | 4 | Maps connection paths; drafts "ask for advice, not a job" outreach with a specific hook. |
| **Interview Prep Coach** | 5 & 6 | Generates ~30 likely questions; drills 2 answers each in a fixed answer structure; post-interview log. |
| **Pipeline Tracker** | 7 | Runs the volume game and follow-up cadence; B-tier-first sequencing. |
| **Negotiation Advisor** | 8 | Market-rate research; ask vs. walk-away numbers; deflection scripts; multi-lever asks. |

## Development status

All five phases and all seven skills are built (116 offline tests passing). Each
phase has a write-up in [`technical documentation/`](technical%20documentation/).

- ✅ **Phase 0 — Foundations:** scaffold, candidate profile schema, shared playbook loader.
- ✅ **Phase 1 — Resume Builder + ATS Optimizer** (highest leverage; shipped first).
- ✅ **Phase 2 — Cover Letter / Email + Company Research.**
- ✅ **Phase 3 — Interview Prep Coach.**
- ✅ **Phase 4 — Networking, Pipeline Tracker, Negotiation Advisor.**
- ✅ **Phase 5 — Job discovery/matching + orchestration.**

The whole flow runs through a single entry point — `ApplicationOrchestrator.prepare(job)`
turns one posting into a tailored resume, an ATS score, an interview question bank,
and (with an LLM writer injected) a cover letter. It runs **fully offline by default**;
inject the LLM writers to upgrade each step to model quality.

See [`CLAUDE.md`](CLAUDE.md) for the full chapter-to-skill mapping and build context.

## CLI

A `job-hunt` command wraps the whole flow. It runs **deterministically by default**
(no API key needed) and defaults to the bundled synthetic profile, so it works
out-of-the-box. Pass `--llm` to enable the model-backed steps (resume rewriting,
cover letter, tailored questions), which require `ANTHROPIC_API_KEY`.

```bash
uv run job-hunt practice                      # interview practice plan + the 12 questions
uv run job-hunt lint                           # resume linter on the sample profile
uv run job-hunt match --jobs jobs.json         # rank postings by fit
uv run job-hunt prepare \                       # build a full application package
    --company "Northwind" --role "Senior PM" \
    --description-file jd.txt --out ./out
uv run job-hunt prepare --job job.json --llm --out ./out   # with LLM steps enabled
uv run job-hunt prepare --company X --role PM --description "..." --save  # persist + track
uv run job-hunt pipeline                       # show tracked apps, projection, follow-ups
uv run job-hunt find --query "AI PM" --rank    # live job search (needs ANTHROPIC_API_KEY)
```

`prepare` builds a tailored resume, scores it against the posting (ATS), assembles an
interview question bank, and — with `--llm` — drafts a cover letter, writing
`resume.md` / `ats.md` / `cover_letter.txt` to the `--out` directory. With `--save` it
persists the package and tracks the application in a workspace (default `.jobhunt`),
which `pipeline` reads back.

## Stack

Python 3.12 via [`uv`](https://github.com/astral-sh/uv), the Anthropic SDK for
tool use, and Claude Code as the build environment. Kept deliberately lean.

## Candidate profiles

All skills read from one **candidate profile** — the verified source of truth for
real experience, metrics, and achievements (see `src/job_hunt_assistant/profile.py`).

- `examples/sample_profile.json` — a **synthetic** fictional candidate, committed
  for tests and development. Load it with `load_sample_profile()`.
- `profiles/` — your **real** profile lives here and is **gitignored**, so personal
  data never lands in this public repo. Load any profile with
  `load_profile("profiles/my_profile.json")`.

## Principle

The playbook's most-repeated warning is **don't lie, don't stretch**. The agent
surfaces and sharpens _real_ achievements from a verified candidate profile — it
never invents them.

## License

[MIT](LICENSE)
