"""
The one piece of code that stays constant across every use case:
research -> tailor -> outreach.

Everything domain-specific (which connectors run, what the LLM is told to
do at each stage, how matches are scored) lives in a PipelineConfig loaded
from YAML. This module has zero knowledge of resumes, VC decks, or grants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.cache import FileCache
from core.connectors import ConnectorRegistry
from core.llm import LLMClient


@dataclass
class PipelineConfig:
    name: str
    connectors: list[str]
    research_prompt: str
    tailor_prompt: str
    outreach_prompt: str
    rubric: dict[str, Any] = field(default_factory=dict)
    validation_prompt: str | None = None  # optional guardrail stage

    @classmethod
    def from_dict(cls, d: dict) -> "PipelineConfig":
        known_keys = {"name", "connectors", "research_prompt", "tailor_prompt", "outreach_prompt", "rubric", "validation_prompt"}
        rubric = dict(d.get("rubric", {}))
        # Any top-level key that isn't a known pipeline field is connector
        # config (e.g. web_search_queries, arxiv_max_results) — merge it
        # into rubric so it reaches connectors, which only receive rubric.
        for key, value in d.items():
            if key not in known_keys:
                rubric[key] = value
        return cls(
            name=d.get("name", "unnamed_pipeline"),
            connectors=d["connectors"],
            research_prompt=d["research_prompt"],
            tailor_prompt=d["tailor_prompt"],
            outreach_prompt=d["outreach_prompt"],
            rubric=rubric,
            validation_prompt=d.get("validation_prompt"),
        )


@dataclass
class PipelineResult:
    entity: str
    raw_research: dict[str, Any]
    findings: str
    tailored_artifact: str
    outreach_message: str
    validation_notes: str | None = None

    def as_dict(self) -> dict:
        return {
            "entity": self.entity,
            "raw_research": self.raw_research,
            "findings": self.findings,
            "tailored_artifact": self.tailored_artifact,
            "outreach_message": self.outreach_message,
            "validation_notes": self.validation_notes,
        }


class Pipeline:
    def __init__(
        self,
        config: PipelineConfig,
        llm: LLMClient,
        registry: ConnectorRegistry,
        cache: FileCache | None = None,
        verbose: bool = True,
    ):
        self.config = config
        self.llm = llm
        self.registry = registry
        self.cache = cache
        self.verbose = verbose

    def run(self, entity: str, personal_artifact: str) -> PipelineResult:
        self._log(f"[1/3] Researching '{entity}' via {self.config.connectors}")
        raw = self._research(entity)

        findings = self.llm.call(self.config.research_prompt, context=raw, entity=entity)
        self._log("[1/3] Research synthesized.")

        self._log("[2/3] Tailoring personal artifact to match findings.")
        tailored = self.llm.call(
            self.config.tailor_prompt,
            context={"findings": findings, "artifact": personal_artifact, "rubric": self.config.rubric},
            entity=entity,
        )

        self._log("[3/3] Drafting outreach message.")
        outreach = self.llm.call(
            self.config.outreach_prompt,
            context={"findings": findings, "tailored_artifact": tailored},
            entity=entity,
        )

        validation_notes = None
        if self.config.validation_prompt:
            self._log("[+] Validating tailored artifact against original (no fabrication check).")
            validation_notes = self.llm.call(
                self.config.validation_prompt,
                context={"original": personal_artifact, "tailored": tailored},
                entity=entity,
            )

        return PipelineResult(
            entity=entity,
            raw_research=raw,
            findings=findings,
            tailored_artifact=tailored,
            outreach_message=outreach,
            validation_notes=validation_notes,
        )

    def _research(self, entity: str) -> dict[str, Any]:
        raw: dict[str, Any] = {}
        for connector_name in self.config.connectors:
            connector = self.registry[connector_name]

            cached = self.cache.get(connector_name, entity, self.config.rubric) if self.cache else None
            if cached is not None:
                self._log(f"    - {connector_name}: cache hit")
                raw[connector_name] = cached
                continue

            try:
                data = connector.fetch(entity, self.config.rubric)
            except Exception as e:  # one flaky connector shouldn't kill the run
                self._log(f"    - {connector_name}: FAILED ({e})")
                data = {"error": str(e)}

            if self.cache:
                self.cache.set(connector_name, entity, self.config.rubric, data)
            raw[connector_name] = data
            self._log(f"    - {connector_name}: ok")
        return raw

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)
