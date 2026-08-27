"""
Generic web search connector. Pluggable backend so you're not locked into
one search API. Reads queries from rubric["web_search_queries"], formats
{entity} into each, and returns raw results per query.

Backends supported out of the box:
  - "tavily"  (TAVILY_API_KEY)   — good default, built for LLM pipelines
  - "serpapi" (SERPAPI_API_KEY)  — Google results
  - "none"    — returns empty results with a note (for offline/testing)

Set RESEARCH_PIPELINE_SEARCH_BACKEND to choose. Defaults to "none" so the
project runs out of the box without any keys configured.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from core.connectors import BaseConnector


class WebSearchConnector(BaseConnector):
    name = "web_search"

    def __init__(self, backend: str | None = None):
        self.backend = backend or os.environ.get("RESEARCH_PIPELINE_SEARCH_BACKEND", "none")

    def fetch(self, entity: str, config: dict) -> dict[str, Any]:
        queries = [q.format(entity=entity) for q in config.get("web_search_queries", [f"{entity} news"])]
        results = {}
        for q in queries:
            results[q] = self._search(q)
        return {"queries": queries, "results": results}

    def _search(self, query: str) -> list[dict]:
        if self.backend == "tavily":
            return self._tavily(query)
        elif self.backend == "serpapi":
            return self._serpapi(query)
        else:
            return [{"note": "No search backend configured. Set RESEARCH_PIPELINE_SEARCH_BACKEND=tavily|serpapi and the matching API key."}]

    def _tavily(self, query: str) -> list[dict]:
        key = os.environ["TAVILY_API_KEY"]
        resp = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query, "max_results": 5},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content")} for r in data.get("results", [])]

    def _serpapi(self, query: str) -> list[dict]:
        key = os.environ["SERPAPI_API_KEY"]
        resp = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": key, "num": 5},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {"title": r.get("title"), "url": r.get("link"), "snippet": r.get("snippet")}
            for r in data.get("organic_results", [])
        ]
