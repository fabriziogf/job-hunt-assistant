# Live providers — web-search-backed research & job discovery

**Status:** Complete · **Scope:** make two pluggable seams real — fill company
research and job postings from a live web search instead of by hand. Built after the
CLI as the first components that reach outside the candidate's own data.

This document covers what the live providers do, how they stay honest, and why they're
built the way they are. It assumes the company-research seam from Phase 2 and the
discovery/orchestration work from Phase 5.

---

## 1. The gap they close

Two parts of the system were always designed as **interfaces with a manual
implementation**, on purpose:

- `ResearchProvider` (Phase 2) — `ManualResearchProvider` returns company facts you
  typed in;
- `JobSource` (added here alongside the live one) — `ManualJobSource` returns postings
  you supplied.

That kept everything offline and testable while the skills were built. The live
providers fill the same interfaces from a real web search, so the rest of the system —
the cover-letter writer, the matcher, the orchestrator — uses them without changing a
line. `WebResearchProvider` *is* a `ResearchProvider`; `WebJobSource` *is* a
`JobSource` (both verified with `isinstance` against the runtime-checkable Protocols in
tests).

---

## 2. Why web search, and not scraping or a job-board API

Two alternatives were rejected:

- **Scraping / a third-party job API** would add dependencies and another API key, and
  scraping is brittle and ToS-fraught — both against the project's "keep the stack
  small" rule.
- **Asking the model to recall facts from memory** is the dangerous one. Chapter 3 is
  explicit that a *wrong* fact in a cover letter is what gets it rejected, and model
  memory is stale and confabulation-prone.

The chosen approach — Claude's **server-side web search tool** via the Anthropic SDK we
already depend on — avoids both. Web search returns *real, current* results *with
citations*, so the facts that reach a cover letter are verifiable, and no new
dependency or key is introduced.

---

## 3. The two-call pattern (`_web.py` + the providers)

Each live provider runs the same two steps, which are deliberately separated:

1. **Search** — a `messages.create` call that declares the `web_search` tool. Claude
   runs the queries server-side and returns a text summary of what it found, with
   sources. The shared `run_web_search()` helper issues this call and collects the
   final text, including handling the server-tool `pause_turn` continuation (when the
   search loop hits its iteration cap, the request is re-sent to resume).
2. **Structure** — a `messages.parse` call that turns that findings text into the
   target schema (`CompanyResearch`, or a list of `JobPosting`), with a system prompt
   that says, in effect, *use only what's in the findings; add nothing.*

**Why two calls instead of one?** Combining the web-search tool with structured output
in a single request mixes a server-side tool loop (which emits citations and
`pause_turn`) with response-format constraints — an awkward, brittle combination.
Splitting them keeps each call doing one simple thing: the first gets real information,
the second shapes it. It also creates a clean honesty boundary — the structuring step
sees only the search findings, so it can't smuggle in outside "knowledge".

---

## 4. Honesty, specific to live data

The live providers introduce a new risk the manual ones didn't have — the model could
*embellish* what search returned — and the design guards against it at the seam:

- the search prompt says report only what's actually found, with source/URL/date per
  fact, and not to fill gaps from memory;
- the extraction prompt says use only facts/postings present in the findings and invent
  nothing;
- `CompanyFact` carries `source`/`url`/`date`, so every claim that reaches paragraph 3
  is traceable, and the candidate can verify it before sending.

This is the same "never fabricate" principle as the rest of the project, applied to a
new failure mode: not "don't invent the candidate's experience" but "don't invent the
*company's* facts".

---

## 5. How they plug in

- **Orchestrator.** `ApplicationOrchestrator(profile, research_provider=WebResearchProvider())`
  — `prepare()` resolves research through the provider exactly as before, so the cover
  letter is now grounded in live facts. A missing/failed lookup still falls back to a
  general letter rather than crashing.
- **CLI.** `prepare --web-research` attaches the live provider (effective together with
  `--llm`, which adds the cover-letter writer that consumes the research). The new
  `find` command drives `WebJobSource` directly — search for real postings, optionally
  `--rank` them against the profile.

Both live classes take an **injected client** (defaulting to `anthropic.Anthropic()`,
which reads `ANTHROPIC_API_KEY`), so tests substitute a fake and run offline.

---

## 6. Testing

Five tests (part of the 127 total), all offline. A fake client stands in for both
`messages.create` (the search step, returning canned findings text) and
`messages.parse` (the structuring step, returning a canned model):

| Test | Checks |
|---|---|
| `WebResearchProvider` is a `ResearchProvider` | Protocol conformance — it really is drop-in. |
| research search-then-structure | The exact requested company name is preserved; facts (with source) come through; the search call declared the `web_search` tool; extraction used the `CompanyResearch` schema. |
| `WebJobSource` is a `JobSource` | Protocol conformance. |
| job source returns & limits | Postings come back as `JobPosting`s and `limit` is honored. |
| `ManualJobSource` filter | Keyword + location filtering works (the offline default). |

The search *quality* isn't (and can't be) unit-tested — that depends on live results.
What's tested is the wiring and the honesty contract: the right tool is declared, the
right schema is used, and the requested identity is preserved.

---

## 7. What's deferred

- **Caching / rate-limiting.** Each `research()` / `search()` is two live calls; a
  cache keyed by company/query would cut cost and latency for repeated runs.
- **Richer job fields.** Salary, posted-date, and seniority could be extracted and fed
  into tier assignment and the negotiation advisor's market range.
- **A live `find`-and-`prepare` pipeline command** that discovers, ranks, and prepares
  the top N in one shot — natural now that both seams are live.

---

## Appendix: glossary

- **Provider / source seam:** an interface (`ResearchProvider`, `JobSource`) the system
  depends on, so the *how* (manual vs. live web) can be swapped without touching
  callers.
- **Server-side web search tool:** an Anthropic-hosted tool you declare in a request;
  Claude runs the searches and returns results with citations — the live providers'
  source of real facts.
- **`pause_turn`:** the stop reason a server-tool loop returns when it hits its
  iteration cap; the request is re-sent to continue. Handled inside `run_web_search()`.
- **Two-call pattern:** search first (get real, cited findings), structure second
  (shape only those findings) — keeping each call simple and the honesty boundary
  clean.
