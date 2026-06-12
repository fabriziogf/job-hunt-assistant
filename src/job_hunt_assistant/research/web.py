"""Live company research via web search (Chapter 3 support).

``WebResearchProvider`` implements the same ``ResearchProvider`` interface as the
manual provider, but fills it from a real web search. It runs two model calls:

1. a web-search request that gathers recent, *sourced* specifics about the
   company (product launches, news, leadership statements, market moves) and the
   hiring manager if discoverable;
2. an extraction call that structures only those findings into
   ``CompanyResearch`` — with the explicit instruction to add nothing not present
   in the findings.

Because the facts come from real search results (each with a source/URL), the
cover-letter writer's paragraph 3 stays grounded in something verifiable rather
than model memory. Drop-in replaceable for ``ManualResearchProvider``.
"""

from __future__ import annotations

from job_hunt_assistant._web import MODEL, SupportsMessages, run_web_search
from job_hunt_assistant.research.company import CompanyResearch

_SEARCH_SYSTEM = """\
You are researching a company so a candidate can write a specific, truthful cover
letter. Use web search to find RECENT, concrete, sourced facts from roughly the
last 12 months: product launches, funding/news, public statements from leadership,
new markets, notable challenges. If you can find the hiring manager or recruiter
for the role, note them. Report only what you actually find, and for each fact
include the source name, URL, and date. Do not speculate or fill gaps from memory."""

_EXTRACT_SYSTEM = """\
Extract the research below into the schema. Use ONLY facts present in the text —
add nothing. Populate each fact's source/url/date when the text provides them.
Categorize each fact. If a hiring manager is named, include it."""


class WebResearchProvider:
    """Fills CompanyResearch from a live web search."""

    def __init__(self, client: SupportsMessages | None = None, model: str = MODEL) -> None:
        self._client = client
        self._model = model

    def _get_client(self) -> SupportsMessages:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def research(self, company: str) -> CompanyResearch:
        client = self._get_client()
        findings = run_web_search(
            client,
            system=_SEARCH_SYSTEM,
            user=(
                f"Research {company} for a job application. Find recent, sourced "
                "specifics and the hiring manager/recruiter if discoverable."
            ),
            model=self._model,
        )
        response = client.messages.parse(
            model=self._model,
            max_tokens=1500,
            system=_EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": findings}],
            output_format=CompanyResearch,
        )
        research = response.parsed_output
        research.company = company  # keep the exact requested name
        return research
