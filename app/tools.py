"""Tools the agent can call. Here: a web-search tool backed by Tavily.
Kept behind a thin wrapper so it can be swapped or mocked in tests (GuardEval).
If no TAVILY_API_KEY is set, returns a clear stub so the graph still runs.
"""
from __future__ import annotations
from functools import lru_cache

from .config import get_settings

settings = get_settings()


@lru_cache
def _tavily():
    from tavily import TavilyClient
    return TavilyClient(api_key=settings.tavily_api_key)


def web_search(query: str, max_results: int = 5) -> str:
    """Search the public web and return a compact text digest."""
    if not settings.tavily_api_key:
        return f"[web search disabled: no TAVILY_API_KEY] query was: {query}"
    res = _tavily().search(query=query, max_results=max_results)
    lines = []
    for r in res.get("results", []):
        title = r.get("title", "")
        url = r.get("url", "")
        content = (r.get("content", "") or "")[:300]
        lines.append(f"- {title} ({url}): {content}")
    return "\n".join(lines) if lines else "No results found."
