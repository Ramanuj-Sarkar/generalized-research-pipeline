"""
arXiv connector — free, no API key. Useful for the grad-school / academic
outreach use case (research a PI's or lab's recent papers).
"""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree

import requests

from core.connectors import BaseConnector

ARXIV_API = "http://export.arxiv.org/api/query"
NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivConnector(BaseConnector):
    name = "arxiv"

    def fetch(self, entity: str, config: dict) -> dict[str, Any]:
        max_results = config.get("arxiv_max_results", 8)
        params = {
            "search_query": f'au:"{entity}"',
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        try:
            resp = requests.get(ARXIV_API, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            return {"papers": [], "error": str(e)}

        root = ElementTree.fromstring(resp.text)
        papers = []
        for entry in root.findall("atom:entry", NS):
            title = entry.findtext("atom:title", default="", namespaces=NS).strip()
            summary = entry.findtext("atom:summary", default="", namespaces=NS).strip()
            published = entry.findtext("atom:published", default="", namespaces=NS)
            link = entry.findtext("atom:id", default="", namespaces=NS)
            papers.append({"title": title, "summary": summary[:500], "published": published, "url": link})

        return {"papers": papers}
