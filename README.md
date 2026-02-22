# Paper Triage Agent

RL environment where an LLM triages research papers. Drop PDFs into an inbox folder, the agent reads them, sorts them into `must-read/`, `nice-to-read/`, or `bullshit/` based on how relevant they are to RLHF and preference-based training, and spits out a prioritized reading order.

Built for the Preference Model assessment.

## Layout

```
environment/   prompt, judge, ground truth, setup
agent/         pydantic-ai triage agent + fastapi wrapper
infra/         docker, deploy script, deps
tests/         judge tests
```

## Running locally or using Claude API

Three ways to run depending on what LLM backend you want. Quick start with Anthropic:

```bash
uv sync
export ANTHROPIC_API_KEY=sk-ant-...
export PAPERS_DIR=/tmp/papers
uv run uvicorn agent.app:app --reload
```

For detailed setup guides:
- **[local_instructions.md](local_instructions.md)** — step by step with LM Studio (local LLM, no API keys)
- **[bedrock.md](bedrock.md)** — using a Bedrock bearer token (same token as Claude Code)

The model backend is controlled by env vars:

| Backend | Env vars |
|---|---|
| Anthropic API | `ANTHROPIC_API_KEY` (default if nothing else set) |
| LM Studio | `LMSTUDIO_URL=http://localhost:1234/v1` |
| AWS Bedrock | `TRIAGE_MODEL=bedrock:us.anthropic.claude-sonnet-4-20250514-v1:0` |

You can also swap any pydantic-ai model string via `TRIAGE_MODEL`.

## Hitting the endpoint

```bash
# health check
curl http://localhost:8000/health

# run triage
curl -X POST http://localhost:8000/triage

# or with a custom papers directory
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"papers_dir": "/tmp/papers"}'
```

## Judge

```bash
uv run python environment/judge.py /papers environment/ground_truth.json
```

Outputs 0-100. Classification accuracy is 40%, ranking correlation (Kendall tau) is 25%, the rest is format checks and keyword overlap. See the docstring in judge.py for the full breakdown.

## Tests

```bash
uv run pytest tests/ -v
```

## Deploying to AWS

WIP
