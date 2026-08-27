# research_pipeline

A generalized **research → tailor → outreach** pipeline. The orchestration
code never changes; every use case (resume/job outreach, VC pitches, grad
school applications, sales prospecting, etc.) is defined entirely by a
YAML config file plus whichever connectors it needs.

## How it works

```
core/pipeline.py   — the invariant orchestrator (research -> tailor -> outreach -> optional validation)
core/connectors.py — BaseConnector interface + registry
core/llm.py         — model-agnostic LLM client (openai / anthropic / stub)
core/cache.py        — on-disk cache so re-runs don't re-hit APIs

connectors/         — one file per source (web_search, arxiv, github, ...)
config/              — one YAML file per use case
```

Three stages run in sequence for every use case:

1. **Research** — configured connectors pull raw data about the target
   entity; an LLM call synthesizes it into findings.
2. **Tailor** — an LLM call rewrites your personal artifact (resume
   bullets, pitch deck section, SOP paragraph, etc.) to mirror the
   target's specific language, constrained by a rubric.
3. **Outreach** — an LLM call drafts a short message using the findings.

An optional 4th **validation** stage checks the tailored artifact for
fabricated claims against the original — recommended to always include.

## Quick start

```bash
pip install -r requirements.txt

# Dry run with no API keys (stub LLM, prints what would be sent):
python cli.py --config config/resume_outreach.yaml \
  --entity "Acme Corp" \
  --artifact examples/sample_resume_bullets.txt

# Real run:
export RESEARCH_PIPELINE_LLM_PROVIDER=anthropic   # or openai
export ANTHROPIC_API_KEY=sk-...
export RESEARCH_PIPELINE_SEARCH_BACKEND=tavily     # or serpapi
export TAVILY_API_KEY=tvly-...

python cli.py --config config/resume_outreach.yaml \
  --entity "Acme Corp" \
  --artifact examples/sample_resume_bullets.txt \
  --out result.json
```

## Included use cases

| Config                        | Entity type | Connectors        | Personal artifact            |
|-------------------------------|-------------|-------------------|------------------------------|
| `config/resume_outreach.yaml` | Company     | web_search        | Resume bullets               |
| `config/vc_pitch.yaml`        | VC fund     | web_search        | Pitch deck excerpt           |
| `config/grad_school.yaml`     | Professor   | arxiv, web_search | Statement of purpose excerpt |

## Adding a new use case

You almost never need to touch `core/`. To add one:

1. **Write a YAML config** (`config/your_use_case.yaml`) with:
   - `connectors`: which sources to pull from
   - connector-specific settings (e.g. `web_search_queries`, using
     `{entity}` as a placeholder) — any top-level key that isn't a
     reserved pipeline field is passed straight through to connectors
   - `research_prompt`, `tailor_prompt`, `outreach_prompt` — plain
     instructions to the LLM for each stage
   - `rubric`: structured matching rules the tailoring stage should
     follow (`match_on`, tone, constraints)
   - optionally `validation_prompt` for the fabrication-check stage

2. **If you need a new source**, add one file to `connectors/`
   implementing `BaseConnector.fetch(entity, config) -> dict`, then
   register it in `core/connectors.py::build_default_registry()`.

3. Run it: `python cli.py --config config/your_use_case.yaml --entity "..." --artifact "..."`.

No other code changes required.

## Notes on the LLM client

`core/llm.py` defaults to a `"stub"` provider that makes no network calls
and no API keys are required — useful for testing pipeline wiring. You can 
switch to real output with:

```bash
export RESEARCH_PIPELINE_LLM_PROVIDER=openai      # or anthropic
export OPENAI_API_KEY=...                          # or ANTHROPIC_API_KEY
```

or you can add to the ```.env``` file:

```bash
RESEARCH_PIPELINE_LLM_PROVIDER=openai      # or anthropic
OPENAI_API_KEY=...                         # or ANTHROPIC_API_KEY
```

The task description mentioned GPT-5.6 as the ideal model — that's the
default model string for the `openai` provider; change it via `--model`
or by editing `LLMClient._default_model()`.

## Notes on connectors

- `web_search.py` needs a backend key (Tavily or SerpAPI) to return real
  results; without one it returns a placeholder note so the pipeline
  still runs end-to-end for testing.
- `arxiv.py` and `github.py` work with no API key (GitHub works better
  with a `GITHUB_TOKEN` to raise rate limits). Note some sandboxed
  network environments block `export.arxiv.org` by default — check your
  egress allowlist if you see connection errors there.

## Guardrails

Fabrication is the main real failure mode of the "tailor" stage
(rewording into overstatement). Every included config wires up a
`validation_prompt` that flags any claim added beyond wording — always
check `validation_notes` in the output before using the tailored artifact.

## Tests

```bash
python tests/test_pipeline.py
```

Runs config-loading checks and an end-to-end smoke test using a fake
connector and the stub LLM — no network or API keys needed.
