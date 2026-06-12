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

## How to use it — step by step (no coding required)

This guide walks you from zero to a polished application. You'll type a few
commands into your computer's **Terminal** — an app that lets you run programs by
typing instead of clicking. Don't worry if you've never used it; just copy and
paste each command exactly, then press **Enter**. The whole setup takes ~15 minutes,
and **everything except the optional "smart AI" features works for free and offline.**

### Step 1 — Open the Terminal

- **Mac:** press `Cmd + Space`, type `Terminal`, press Enter.
- **Windows:** press the Start button, type `PowerShell`, press Enter.
- **Linux:** open your **Terminal** app.

A window with a blinking cursor appears. That's where you'll paste commands.

### Step 2 — Install `uv` (the tool that runs everything)

Copy-paste the line for your system, press Enter, and wait for it to finish.

```bash
# Mac or Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell):
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then **close the Terminal window and open a new one** (so it picks up the new tool).

### Step 3 — Download this project

```bash
git clone https://github.com/fabriziogf/job-hunt-assistant.git
cd job-hunt-assistant
```

> No `git`? Instead, click the green **Code** button at the top of the
> [GitHub page](https://github.com/fabriziogf/job-hunt-assistant) → **Download ZIP**,
> unzip it, then in the Terminal type `cd ` (with a space) and drag the unzipped
> folder onto the Terminal window and press Enter.

### Step 4 — Set it up (one time)

```bash
uv sync
```

This installs everything the project needs. You only do this once.

### Step 5 — Try it immediately (with the built-in example)

You can use every feature right away with a built-in **example candidate**, before
adding your own details:

```bash
uv run job-hunt practice
```

You'll see an interview-practice plan and the 12 questions you'll almost certainly be
asked. **If that printed a list, everything is working.** 🎉

### Step 6 — Add your own details (your "profile")

The agent works from a single file describing your experience — your **profile**.
The easiest way to create one:

1. Open the example file `examples/sample_profile.json` to see the shape.
2. Open a plain-text editor (**Mac:** TextEdit → *Format → Make Plain Text*;
   **Windows:** Notepad) and create your own, using this template:

```json
{
  "contact": {
    "full_name": "Your Name",
    "email": "you@example.com",
    "phone": "(555) 555-5555",
    "location": "City, ST",
    "linkedin": "https://www.linkedin.com/in/you/"
  },
  "headline": "What you do in a few words",
  "summary": "A sentence or two about your experience.",
  "experiences": [
    {
      "company": "Your Employer",
      "title": "Your Job Title",
      "location": "City, ST",
      "start": "2022-01-01",
      "end": null,
      "brands": ["A well-known client or tool you used"],
      "achievements": [
        {
          "what": "What you accomplished",
          "measured_by": "the number that proves it (%, $, time)",
          "how": "how you did it",
          "verified": true
        }
      ]
    }
  ],
  "education": [
    {
      "institution": "Your School",
      "degree": "Your Degree",
      "field_of_study": "Your Major",
      "graduation": "2021-06-01",
      "gpa": 3.8
    }
  ],
  "skills": [{ "name": "A skill" }, { "name": "Another skill" }]
}
```

3. Create a folder named `profiles` inside the project folder (if it isn't there
   already), and save your file inside it as `my_profile.json` — so the full path is
   `profiles/my_profile.json`. (Anything in `profiles/` stays private on your
   computer and is never uploaded.)

> **Shortcut:** paste the template above into ChatGPT or Claude with *"Fill this out
> from my resume:"* and your resume text, then save the result. Set `"verified": true`
> only on achievements that are genuinely true — the agent refuses to make things up.

Now add `--profile profiles/my_profile.json` to any command to use **your** details.

### Step 7 — Check your resume and prepare an application (free, offline)

Point the agent at a job you're interested in. Replace the text in quotes with the
real role and the job posting:

```bash
# Check your resume against the playbook's rules:
uv run job-hunt lint --profile profiles/my_profile.json

# Prepare a tailored application for one job:
uv run job-hunt prepare \
    --profile profiles/my_profile.json \
    --company "Acme Corp" \
    --role "Product Manager" \
    --description "Paste the job description here" \
    --out ./acme
```

`prepare` tailors your resume to that job, scores how well it matches (the same way
company software screens resumes — aim for 75%+), lists the keywords you're missing,
and saves the files into a folder (here, `acme`). Open `acme/resume.md` to read it.

### Step 8 — Track your applications over time

```bash
# Save this application and add it to your tracker:
uv run job-hunt prepare --profile profiles/my_profile.json \
    --company "Acme Corp" --role "Product Manager" \
    --description "..." --save

# See everything you've applied to, plus which follow-ups are due:
uv run job-hunt pipeline
```

Your tracker lives in a folder called `.jobhunt`. Come back any time and run
`uv run job-hunt pipeline` to see what needs a follow-up (the playbook says: every 2
weeks, for 6 weeks).

### Step 9 (optional) — Turn on the "smart AI" features

By default the agent uses fixed rules — fast, free, and private. To also have AI
**rewrite** your resume bullets, **draft a cover letter**, and **search live job
boards**, you need an Anthropic API key (this is a paid service — you pay per use):

1. Create a key at [console.anthropic.com](https://console.anthropic.com) → *API Keys*.
2. Tell the Terminal your key (do this each time you open a new Terminal window):

```bash
# Mac or Linux:
export ANTHROPIC_API_KEY="paste-your-key-here"

# Windows (PowerShell):
$env:ANTHROPIC_API_KEY="paste-your-key-here"
```

3. Add `--llm` to draft a cover letter, or use `find` to search live job listings:

```bash
uv run job-hunt prepare --profile profiles/my_profile.json \
    --company "Acme Corp" --role "Product Manager" \
    --description "..." --llm --out ./acme

uv run job-hunt find --query "product manager" --location "Boston" --rank
```

### Command cheat sheet

| What you want | Command |
|---|---|
| See the interview practice plan | `uv run job-hunt practice` |
| Check your resume for problems | `uv run job-hunt lint --profile profiles/my_profile.json` |
| Prepare an application for a job | `uv run job-hunt prepare --profile profiles/my_profile.json --company "X" --role "Y" --description "..." --out ./out` |
| Save it and track it | add `--save` to the `prepare` command |
| See your tracked applications | `uv run job-hunt pipeline` |
| Also draft a cover letter (needs API key) | add `--llm` to the `prepare` command |
| Search live job listings (needs API key) | `uv run job-hunt find --query "..." --rank` |
| See all options for any command | add `--help`, e.g. `uv run job-hunt prepare --help` |

### If something goes wrong

- **`command not found: uv`** — close the Terminal and open a new window (Step 2),
  then try again.
- **`command not found: job-hunt`** — make sure you ran `uv sync` (Step 4) and that
  you're inside the `job-hunt-assistant` folder (`cd job-hunt-assistant`).
- **An error mentioning `ANTHROPIC_API_KEY`** — you used `--llm` or `find` without a
  key; either set one (Step 9) or drop `--llm` to use the free offline features.
- **Anything else** — add `--help` to your command to see the available options.

## Skills

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

All five phases and all seven skills are built (136 offline tests passing). Each
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
