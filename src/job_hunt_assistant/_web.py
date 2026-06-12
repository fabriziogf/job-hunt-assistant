"""Shared helper for the live (web-search-backed) providers.

The live ``ResearchProvider`` and ``JobSource`` both work the same way: run a
Claude request with the server-side **web search tool** to gather real, current,
cited findings, then structure those findings in a second call. This module
holds the piece they share — issuing the web-search request and collecting the
model's final text — so neither provider reimplements the tool loop.

Web search is an Anthropic-hosted tool: you declare it and Claude runs the
queries server-side, returning results with citations. That's what keeps the
live providers honest — facts come from real search results, not model memory.
"""

from __future__ import annotations

from typing import Any, Protocol

MODEL = "claude-opus-4-8"

# Server-side web search tool (see the Anthropic tool-use docs).
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}


class SupportsMessages(Protocol):
    @property
    def messages(self) -> Any: ...


def _collect_text(content: list) -> str:
    """Join all text blocks of a response into one string."""
    return "\n".join(
        block.text for block in content if getattr(block, "type", None) == "text"
    )


def run_web_search(
    client: SupportsMessages,
    *,
    system: str,
    user: str,
    model: str = MODEL,
    max_tokens: int = 2048,
    max_rounds: int = 4,
) -> str:
    """Run a web-search-backed request and return the model's final text.

    Handles the server-tool ``pause_turn`` continuation: when the server-side
    search loop hits its iteration cap, the request is re-sent to resume, up to
    ``max_rounds`` times.
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        tools=[WEB_SEARCH_TOOL],
        messages=[{"role": "user", "content": user}],
    )
    rounds = 0
    while getattr(response, "stop_reason", None) == "pause_turn" and rounds < max_rounds:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            tools=[WEB_SEARCH_TOOL],
            messages=[
                {"role": "user", "content": user},
                {"role": "assistant", "content": response.content},
            ],
        )
        rounds += 1
    return _collect_text(response.content)
