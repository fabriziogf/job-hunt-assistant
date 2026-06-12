# Persistence — saving the state a job hunt accumulates

**Status:** Complete · **Scope:** a storage layer so the durable artifacts of a job
hunt — the pipeline, interview logs, saved application packages, cached company
research — survive between runs. Built after the live providers.

This document covers what persistence stores, how it's structured, and the reasoning.
It assumes the skills (Phases 0–5), the CLI, and the live providers.

---

## 1. What needed persisting, and what didn't

Most of the system is **stateless** — building a resume or scoring an ATS match is a
pure function of its inputs, so there's nothing to save. But a real job hunt runs over
*months*, and a few things genuinely accumulate:

- **The pipeline** — applications you add and update over weeks (the clearest case).
- **Interview logs** — one debrief per interview, built up over time.
- **Application packages** — the generated resume/ATS/cover-letter bundle per job,
  worth keeping rather than regenerating.
- **Company research** — expensive to fetch live; worth caching per company.

Persistence targets exactly these. It deliberately does **not** try to be a database
or an ORM — every model is already JSON-able Pydantic, so the job is just organizing
JSON files on disk well.

---

## 2. Atomic writes (`save_model` / `load_model`)

The two primitives are `save_model(model, path)` and `load_model(cls, path)`. Loading
is a one-liner over Pydantic's validating JSON parser. Saving is the part that earns
its keep: it writes to a **temp file in the same directory, then `os.replace()`s** it
into place.

`os.replace` is atomic on the same filesystem, so a reader never sees a half-written
file and a crash mid-write can't corrupt the existing one — it either has the old
complete file or the new complete file. That matters most for `pipeline.json`, which
is read-modify-written every time you track an application; a naive truncate-and-write
could leave it unloadable if interrupted. On any failure the temp file is cleaned up.

---

## 3. The `Workspace`

A `Workspace` is a single directory holding one job hunt's state, with typed accessors
so callers never hand-build paths:

```
<root>/
  profile.json                      load_profile() / save_profile()
  pipeline.json                     load_pipeline() / save_pipeline() / track()
  logs/<company>-<date>.json        save_interview_log() / load_interview_logs()
  packages/<company>-<role>.json    save_package() / load_packages()
  research/<company>.json           cache_research() / get_research()
```

Design notes:

- **Sensible empty states.** `load_pipeline()` returns an empty `Pipeline()` when none
  exists yet, and `load_interview_logs()` / `load_packages()` return `[]` — so a fresh
  workspace "just works" without existence checks at the call site.
- **`track(application)`** is the one convenience that bundles the common
  read-modify-write: load the pipeline, append, save. It's what `prepare --save` calls.
- **Slugified filenames.** Collections (logs, packages, research) get one file each,
  named by a filesystem-safe slug (`Northwind Commerce` → `northwind-commerce`). One
  file per item keeps writes small and lets you eyeball/diff/delete individual
  artifacts. `slugify()` is also what makes the research cache lookup case-insensitive.

---

## 4. `CachedResearchProvider` — where persistence meets the live layer

The live-providers doc flagged caching as deferred; this is it.
`CachedResearchProvider` wraps **any** `ResearchProvider` (manual or web) and backs it
with a `Workspace`:

```
research(company):
    hit = workspace.get_research(company)   # cached?
    if hit: return hit
    result = inner.research(company)        # else delegate (maybe a live, billable call)
    workspace.cache_research(result)        # and remember it
    return result
```

Because it satisfies the same `ResearchProvider` interface, it composes transparently:
`CachedResearchProvider(WebResearchProvider(), ws)` is a drop-in that turns the
expensive live lookup into a once-per-company cost. This is the payoff of having kept
research behind an interface since Phase 2 — caching slots in as a decorator without
any skill knowing.

---

## 5. CLI surface

Two additions make persistence usable from the terminal:

- **`prepare --save [--workspace DIR]`** — after building the package, save it under
  `packages/` and `track()` the application into `pipeline.json`. `--workspace`
  defaults to `.jobhunt`.
- **`pipeline [--workspace DIR]`** — read the persisted pipeline back and print the
  tracked applications, the status counts, the funnel projection (Ch. 7 volume math),
  and any follow-ups due today (the Ch. 7 every-2-weeks-for-6-weeks cadence).

Together these close the loop the Pipeline Tracker (Phase 4) implied but couldn't
deliver while everything was in-memory: apply → save → come back next week → see
what's due.

---

## 6. Testing

Nine tests across persistence and the CLI, all offline:

| Area | Checks |
|---|---|
| `save_model`/`load_model` | Round-trips a `Pipeline`; no `.tmp` file is left behind (atomicity). |
| `slugify` | Spaces/punctuation/empty handled. |
| `Workspace` pipeline | `track()` persists, and a *fresh* `Workspace` over the same dir sees the saved applications (real cross-run persistence). |
| `Workspace` logs | Interview logs save to slug-named files and load back. |
| Research cache | `get_research` is case-insensitive; `CachedResearchProvider` delegates only on a miss (the inner provider is called exactly once for two reads). |
| CLI | `prepare --save` writes the package + pipeline and the `pipeline` command reads them back; an empty workspace prints a friendly message. |

The cross-run test (re-opening a `Workspace` over the same `tmp_path`) is the one that
actually proves persistence rather than just serialization.

---

## 7. What's deferred

- **Concurrency.** Atomic writes prevent torn files, but two processes writing the same
  pipeline could still lose an update (last-writer-wins). A lock file would fix it;
  unnecessary for a single-user CLI today.
- **Migrations.** If a model's schema changes, old JSON may fail validation. A
  versioned schema + migration step would handle that when it arises.
- **A `workspace`/`logs` CLI surface.** Listing or pruning saved packages and logs from
  the CLI is a small follow-on now that the `Workspace` methods exist.

---

## Appendix: glossary

- **Atomic write:** writing to a temporary file then renaming it over the target, so a
  reader only ever sees a complete file — here via `os.replace`.
- **Workspace:** a directory that holds one job hunt's durable state, with typed
  accessors instead of raw paths.
- **Slug:** a filesystem-safe, lowercased, hyphenated version of a name, used for
  per-item filenames and case-insensitive cache lookups.
- **Decorator (provider):** `CachedResearchProvider` wraps another provider with the
  same interface, adding caching without the wrapped provider or its callers changing.
