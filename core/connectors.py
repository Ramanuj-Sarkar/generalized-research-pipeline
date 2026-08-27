"""
Connector base class + registry.

Every connector fetches raw source material for a given entity. Connectors
know nothing about tailoring or outreach — they only pull and lightly
structure data. Swap connectors in/out per use case entirely via config
(the `connectors:` list in each YAML file).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, entity: str, config: dict) -> dict[str, Any]:
        """
        Fetch raw data about `entity`. `config` is the full rubric/config
        dict for the pipeline run, so a connector can read its own
        namespaced keys (e.g. config.get("web_search_queries")).

        Must return a JSON-serializable dict. Should not raise on
        "no results found" — return {"results": [], "note": "..."} instead,
        so one flaky source doesn't kill the whole research stage.
        """
        raise NotImplementedError


class ConnectorRegistry:
    def __init__(self):
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        self._connectors[connector.name] = connector

    def __getitem__(self, name: str) -> BaseConnector:
        if name not in self._connectors:
            raise KeyError(
                f"No connector registered under '{name}'. "
                f"Available: {list(self._connectors)}"
            )
        return self._connectors[name]

    def __contains__(self, name: str) -> bool:
        return name in self._connectors

    def names(self) -> list[str]:
        return list(self._connectors)


def build_default_registry() -> ConnectorRegistry:
    """Registers all built-in connectors. Import lazily to keep this cheap."""
    from connectors.web_search import WebSearchConnector
    from connectors.arxiv import ArxivConnector
    from connectors.github import GitHubConnector

    registry = ConnectorRegistry()
    registry.register(WebSearchConnector())
    registry.register(ArxivConnector())
    registry.register(GitHubConnector())
    return registry
