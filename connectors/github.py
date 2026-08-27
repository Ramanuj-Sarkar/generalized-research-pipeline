"""
GitHub connector — uses the public REST API (api.github.com). Works
unauthenticated at low rate limits; set GITHUB_TOKEN for higher limits.
Useful for the "recruiting: research a candidate" or "research an OSS
maintainer" use cases.
"""

from __future__ import annotations

import os
from typing import Any

import requests

from core.connectors import BaseConnector


class GitHubConnector(BaseConnector):
    name = "github"

    def fetch(self, entity: str, config: dict) -> dict[str, Any]:
        """`entity` is treated as a GitHub username or org login."""
        headers = {"Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            profile = requests.get(f"https://api.github.com/users/{entity}", headers=headers, timeout=15)
            profile.raise_for_status()
            repos = requests.get(
                f"https://api.github.com/users/{entity}/repos",
                headers=headers,
                params={"sort": "pushed", "per_page": config.get("github_max_repos", 8)},
                timeout=15,
            )
            repos.raise_for_status()
        except requests.RequestException as e:
            return {"profile": {}, "repos": [], "error": str(e)}

        p = profile.json()
        r = repos.json()
        return {
            "profile": {"name": p.get("name"), "bio": p.get("bio"), "company": p.get("company"), "blog": p.get("blog")},
            "repos": [
                {"name": repo.get("name"), "description": repo.get("description"), "language": repo.get("language"), "pushed_at": repo.get("pushed_at")}
                for repo in r
            ],
        }
