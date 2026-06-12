"""Tests for the company research capability."""

import pytest

from job_hunt_assistant import (
    CompanyFact,
    CompanyResearch,
    ManualResearchProvider,
    ResearchProvider,
)


def _sample() -> CompanyResearch:
    return CompanyResearch(
        company="Northwind Commerce",
        hiring_manager_name="Dana Chen",
        hiring_manager_title="Director of Product",
        facts=[
            CompanyFact(text="Launched a same-day delivery network", source="blog"),
        ],
    )


def test_has_specifics_and_best_fact():
    r = _sample()
    assert r.has_specifics
    assert r.best_fact().text.startswith("Launched")

    empty = CompanyResearch(company="X")
    assert not empty.has_specifics
    assert empty.best_fact() is None


def test_manual_provider_lookup_case_insensitive():
    provider = ManualResearchProvider([_sample()])
    assert isinstance(provider, ResearchProvider)  # satisfies the interface
    got = provider.research("northwind commerce")  # different case
    assert got.hiring_manager_name == "Dana Chen"


def test_manual_provider_raises_on_unknown_company():
    provider = ManualResearchProvider([_sample()])
    with pytest.raises(KeyError, match="never invents"):
        provider.research("Unknown Co")
