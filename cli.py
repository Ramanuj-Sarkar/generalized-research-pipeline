#!/usr/bin/env python3
"""
CLI entry point.

Usage:
  python cli.py --config config/resume_outreach.yaml \
                 --entity "Acme Corp" \
                 --artifact my_resume_bullets.txt \
                 --out result.json

  python cli.py --config config/vc_pitch.yaml \
                 --entity "Sequoia Capital" \
                 --artifact pitch_deck_excerpt.txt

If --artifact is omitted, reads the personal artifact from stdin.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from core.cache import FileCache
from core.connectors import build_default_registry
from core.llm import LLMClient
from core.pipeline import Pipeline, PipelineConfig


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generalized research -> tailor -> outreach pipeline")
    parser.add_argument("--config", required=True, help="Path to a YAML pipeline config")
    parser.add_argument("--entity", required=True, help="The target entity name (company, fund, professor, username, etc.)")
    parser.add_argument("--artifact", help="Path to the personal artifact file (resume bullets, pitch excerpt, SOP excerpt). Reads stdin if omitted.")
    parser.add_argument("--out", help="Path to write the JSON result. Prints to stdout if omitted.")
    parser.add_argument("--provider", default=None, help="LLM provider: openai | anthropic | stub (default: stub, or $RESEARCH_PIPELINE_LLM_PROVIDER)")
    parser.add_argument("--model", default=None, help="Override model name for the chosen provider")
    parser.add_argument("--no-cache", action="store_true", help="Disable the on-disk research cache")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress logging")
    args = parser.parse_args()

    config_dict = yaml.safe_load(Path(args.config).read_text())
    config = PipelineConfig.from_dict(config_dict)

    artifact = Path(args.artifact).read_text() if args.artifact else sys.stdin.read()

    llm = LLMClient(provider=args.provider, model=args.model)
    registry = build_default_registry()
    cache = None if args.no_cache else FileCache()

    pipeline = Pipeline(config=config, llm=llm, registry=registry, cache=cache, verbose=not args.quiet)
    result = pipeline.run(entity=args.entity, personal_artifact=artifact)

    output = json.dumps(result.as_dict(), indent=2)
    if args.out:
        Path(args.out).write_text(output)
        if not args.quiet:
            print(f"\nWrote result to {args.out}")
    else:
        print("\n" + "=" * 60)
        print(output)


if __name__ == "__main__":
    main()
