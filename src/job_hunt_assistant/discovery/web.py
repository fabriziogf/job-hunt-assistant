"""Live job discovery via web search.

``WebJobSource`` implements the ``JobSource`` interface from a real web search:
one web-search call to find current postings matching a query, then an extraction
call that structures the findings into ``JobPosting`` objects. Drop-in
replaceable for ``ManualJobSource``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from job_hunt_assistant._web import MODEL, SupportsMessages, run_web_search
from job_hunt_assistant.discovery.match import JobPosting

_SEARCH_SYSTEM = """\
You help a candidate find real, currently-open job postings. Use web search to
find genuine openings matching the query. For each, capture the company, the
exact role title, a faithful summary of the description/requirements, the
location, and the posting URL. Report only real postings you actually find — do
not invent roles or companies."""

_EXTRACT_SYSTEM = """\
Extract the job postings below into the schema. Use ONLY postings present in the
text — invent nothing. Keep the role title and description faithful to the source,
and include the location and URL when available."""


class _JobPostings(BaseModel):
    jobs: list[JobPosting] = Field(default_factory=list)


class WebJobSource:
    """Finds real job postings via a live web search."""

    def __init__(self, client: SupportsMessages | None = None, model: str = MODEL) -> None:
        self._client = client
        self._model = model

    def _get_client(self) -> SupportsMessages:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def search(
        self, query: str, *, location: str | None = None, limit: int = 10
    ) -> list[JobPosting]:
        client = self._get_client()
        ask = f"Find up to {limit} current job postings for: {query}"
        if location:
            ask += f" in {location}"
        findings = run_web_search(
            client, system=_SEARCH_SYSTEM, user=ask + ".", model=self._model
        )
        response = client.messages.parse(
            model=self._model,
            max_tokens=2048,
            system=_EXTRACT_SYSTEM,
            messages=[{"role": "user", "content": findings}],
            output_format=_JobPostings,
        )
        return response.parsed_output.jobs[:limit]
