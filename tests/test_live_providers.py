"""Tests for the live (web-search-backed) providers, using a fake client.

No network or API key: the fake stands in for the Anthropic client's
``messages.create`` (the web-search step) and ``messages.parse`` (the structuring
step). These verify the wiring and the honesty contract, not search quality.
"""

from types import SimpleNamespace

from job_hunt_assistant import (
    CompanyFact,
    CompanyResearch,
    JobPosting,
    JobSource,
    ManualJobSource,
    WebJobSource,
    WebResearchProvider,
)
from job_hunt_assistant.discovery.web import _JobPostings
from job_hunt_assistant.research.company import ResearchProvider


def _text_block(text: str):
    return SimpleNamespace(type="text", text=text)


class _FakeMessages:
    """Fake .create (web search) + .parse (extraction)."""

    def __init__(self, search_text: str, parsed):
        self._search_text = search_text
        self._parsed = parsed
        self.create_calls: list[dict] = []
        self.parse_calls: list[dict] = []

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        return SimpleNamespace(
            content=[_text_block(self._search_text)], stop_reason="end_turn"
        )

    def parse(self, **kwargs):
        self.parse_calls.append(kwargs)
        return SimpleNamespace(parsed_output=self._parsed)


class _FakeClient:
    def __init__(self, search_text: str, parsed):
        self.messages = _FakeMessages(search_text, parsed)


# --- WebResearchProvider -----------------------------------------------------


def test_web_research_satisfies_provider_protocol():
    provider = WebResearchProvider(client=_FakeClient("", CompanyResearch(company="x")))
    assert isinstance(provider, ResearchProvider)


def test_web_research_searches_then_structures():
    parsed = CompanyResearch(
        company="(to be overwritten)",
        hiring_manager_name="Dana Chen",
        facts=[
            CompanyFact(
                text="launched same-day delivery",
                source="TechCrunch",
                url="https://example.com/a",
            )
        ],
    )
    client = _FakeClient("Findings: Northwind launched same-day delivery...", parsed)
    provider = WebResearchProvider(client=client)

    research = provider.research("Northwind Commerce")

    # The exact requested company name is preserved.
    assert research.company == "Northwind Commerce"
    assert research.has_specifics
    assert research.facts[0].source == "TechCrunch"
    # The search call declared the web_search tool.
    assert client.messages.create_calls[0]["tools"][0]["type"].startswith("web_search")
    # Extraction used the structured schema.
    assert client.messages.parse_calls[0]["output_format"] is CompanyResearch


# --- WebJobSource ------------------------------------------------------------


def test_web_job_source_satisfies_source_protocol():
    source = WebJobSource(client=_FakeClient("", _JobPostings()))
    assert isinstance(source, JobSource)


def test_web_job_source_returns_and_limits_postings():
    parsed = _JobPostings(
        jobs=[
            JobPosting(company=f"Co{i}", role="PM", description="d") for i in range(5)
        ]
    )
    source = WebJobSource(client=_FakeClient("found 5 postings", parsed))
    jobs = source.search("product manager", location="Seattle", limit=3)
    assert len(jobs) == 3  # limit applied
    assert all(isinstance(j, JobPosting) for j in jobs)


# --- ManualJobSource (offline default) ---------------------------------------


def test_manual_job_source_keyword_and_location_filter():
    source = ManualJobSource(
        [
            JobPosting(company="Fit Co", role="ML PM", description="recommender systems", location="Seattle, WA"),
            JobPosting(company="Other", role="Chef", description="pastry", location="Boston, MA"),
        ]
    )
    assert isinstance(source, JobSource)
    results = source.search("recommender", location="Seattle")
    assert len(results) == 1
    assert results[0].company == "Fit Co"
