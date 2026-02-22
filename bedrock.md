# Running with Bedrock Bearer Token

If you already use Claude Code with a Bedrock token helper (e.g. via Teleport), you can reuse the same token to run this agent. No Anthropic API key needed.

## Prerequisites

- Bedrock token already working for Claude Code (check `~/.cache/bedrock-tokens/token.txt`)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

## 1. Install dependencies

```bash
cd /path/to/interview
uv sync
```

## 2. Download test papers

```bash
# Set up the papers directory
export PAPERS_DIR=/tmp/papers

# Download papers from the papers.json file (creates real PDFs from ArXiv)
uv run python download_papers.py --inbox /tmp/papers/inbox
```

This will:
- Download real academic papers as PDFs into `/tmp/papers/inbox/`
- Automatically generate the matching `environment/ground_truth.json`
- Create the proper directory structure (`must-read/`, `nice-to-read/`, `bullshit/`)
- Rate-limit ArXiv requests to be respectful

The papers are categorized as:
- **must-read**: AI and RL papers (RLHF, DPO, reward modeling, etc.)
- **nice-to-read**: MLOps and ML engineering papers
- **bullshit**: Off-topic papers (fashion, culture, etc.)

**Note**: You need a `papers.json` file with the paper URLs. If you don't have one, you can create a minimal test set by making a simple `papers.json`:

```bash
cat > papers.json << 'EOF'
{
  "arxiv_papers": [
    {
      "title": "Direct Preference Optimization: Your Language Model is Secretly a Reward Model",
      "url": "https://arxiv.org/abs/2305.18290",
      "category": "AI and RL (2026)"
    },
    {
      "title": "MLOps: Overview, Definition, and Architecture",
      "url": "https://example.com/mlops-paper.pdf",
      "category": "MLOps"
    },
    {
      "title": "Fashion Trends in Social Media",
      "url": "https://example.com/fashion-paper.pdf",
      "category": "Fashion"
    }
  ]
}
EOF
```

## 3. Run the agent

```bash
export AWS_BEARER_TOKEN_BEDROCK=$(cat ~/.cache/bedrock-tokens/token.txt)
export AWS_DEFAULT_REGION=eu-west-1
export TRIAGE_MODEL=bedrock:eu.anthropic.claude-sonnet-4-20250514-v1:0
export PAPERS_DIR=/tmp/papers
export PYTHONPATH=$(pwd)

uv run uvicorn agent.app:app --reload --port 8000
```

Leave this terminal running.

## 4. Fire the triage

In another terminal:

```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"papers_dir": "/tmp/papers"}'
```

## 5. Check results

```bash
ls /tmp/papers/must-read/
ls /tmp/papers/nice-to-read/
ls /tmp/papers/bullshit/

cat /tmp/papers/reading_order.txt
cat /tmp/papers/reading_order.txt

# score against ground truth
PYTHONPATH=$(pwd) uv run python environment/judge.py /tmp/papers environment/ground_truth.json
```

