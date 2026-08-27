"""
Model-agnostic LLM client wrapper.

Swap providers by changing `provider` in the constructor or via the
RESEARCH_PIPELINE_LLM_PROVIDER env var. Each provider implementation only
needs to satisfy `_call_raw(system_prompt, user_content) -> str`.

Providers included:
  - "openai"     : uses OPENAI_API_KEY, defaults to gpt-5.6 (fallback gpt-4o)
  - "anthropic"  : uses ANTHROPIC_API_KEY, defaults to claude-sonnet-4-6
  - "stub"       : no network calls, deterministic canned output — useful
                    for testing the pipeline wiring without burning API
                    credits or needing keys configured.
"""

from __future__ import annotations

import json
import os
from typing import Any


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = provider or os.environ.get("RESEARCH_PIPELINE_LLM_PROVIDER", "stub")
        self.model = model or self._default_model()

    def _default_model(self) -> str:
        return {
            "openai": "gpt-5.6",
            "anthropic": "claude-sonnet-4-6",
            "stub": "stub-model",
        }.get(self.provider, "stub-model")

    def call(self, prompt_template: str, context: Any, entity: str | None = None) -> str:
        """
        Fill the prompt template with {entity} if present, attach context as
        structured data, and call the underlying provider.
        """
        system_prompt = prompt_template.format(entity=entity) if entity else prompt_template
        user_content = self._render_context(context)

        if self.provider == "stub":
            return self._call_stub(system_prompt, user_content)
        elif self.provider == "openai":
            return self._call_openai(system_prompt, user_content)
        elif self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_content)
        else:
            raise LLMError(f"Unknown provider: {self.provider}")

    @staticmethod
    def _render_context(context: Any) -> str:
        if isinstance(context, str):
            return context
        try:
            return json.dumps(context, indent=2, default=str)
        except TypeError:
            return str(context)

    # ---- providers ----

    def _call_stub(self, system_prompt: str, user_content: str) -> str:
        return (
            "[STUB OUTPUT — no LLM call made]\n"
            f"System prompt: {system_prompt[:200]}...\n"
            f"Context length: {len(user_content)} chars\n"
            "Set RESEARCH_PIPELINE_LLM_PROVIDER=openai|anthropic and the "
            "matching API key env var to get real output."
        )

    def _call_openai(self, system_prompt: str, user_content: str) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise LLMError("pip install openai to use the openai provider") from e

        client = OpenAI()
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )
        return resp.choices[0].message.content

    def _call_anthropic(self, system_prompt: str, user_content: str) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise LLMError("pip install anthropic to use the anthropic provider") from e

        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=self.model,
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")
