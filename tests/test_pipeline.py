"""
Smoke tests for the pipeline wiring — verifies config loading, connector
registry, and end-to-end run using the stub LLM provider (no network,
no API keys needed).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

from core.connectors import BaseConnector, ConnectorRegistry
from core.llm import LLMClient
from core.pipeline import Pipeline, PipelineConfig


class FakeConnector(BaseConnector):
    """Deterministic connector for tests — no network."""
    name = "fake"

    def fetch(self, entity: str, config: dict) -> dict:
        return {"note": f"fake data about {entity}"}


def test_config_loads_from_yaml():
    for path in Path(__file__).parent.parent.glob("config/*.yaml"):
        config_dict = yaml.safe_load(path.read_text())
        config = PipelineConfig.from_dict(config_dict)
        assert config.connectors, f"{path} defines no connectors"
        assert config.research_prompt
        assert config.tailor_prompt
        assert config.outreach_prompt
        print(f"OK: {path.name} -> connectors={config.connectors}")


def test_end_to_end_with_stub_llm_and_fake_connector():
    config = PipelineConfig(
        name="test",
        connectors=["fake"],
        research_prompt="Summarize findings about {entity}.",
        tailor_prompt="Tailor this artifact.",
        outreach_prompt="Draft outreach.",
        rubric={"match_on": ["x"]},
    )
    registry = ConnectorRegistry()
    registry.register(FakeConnector())
    llm = LLMClient(provider="stub")

    pipeline = Pipeline(config=config, llm=llm, registry=registry, cache=None, verbose=False)
    result = pipeline.run(entity="Test Corp", personal_artifact="- did a thing")

    assert result.entity == "Test Corp"
    assert "fake" in result.raw_research
    assert result.findings
    assert result.tailored_artifact
    assert result.outreach_message
    print("OK: end-to-end run with stub LLM + fake connector")


if __name__ == "__main__":
    test_config_loads_from_yaml()
    test_end_to_end_with_stub_llm_and_fake_connector()
    print("\nAll smoke tests passed.")
