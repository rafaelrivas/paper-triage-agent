# Running with LM Studio

Step by step for getting this thing working on your machine with a local model. No API keys, no cloud bills, just your GPU doing the work.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- [LM Studio](https://lmstudio.ai/) installed
- A decent GPU. 16GB VRAM minimum for quantized 70B models, 8GB if you're running something smaller (but expect worse results). with a macbook m4 max it took like 12 mins, really freaking slow! but I can spend more time if needed to optimize.

## 1. Install dependencies

```bash
cd /path/to/interview
uv sync
```

## 2. Download the test papers

We need some PDFs in the inbox for the agent to triage. Use the provided download script to get real papers:

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

## 3. Set up LM Studio

1. Open LM Studio
2. Go to the **Discover** tab, download a model. Recommendations:
   - **Best results**: `Qwen2.5-72B-Instruct` (Q4 quantization, needs ~40GB VRAM)
   - **Good enough**: `Qwen2.5-32B-Instruct` (Q4, ~20GB VRAM)
   - **Will probably work**: `Llama-3.1-70B-Instruct` or `Mistral-Large`
   - **Probably won't work well**: anything under 14B — structured JSON output gets flaky
3. Load the model
4. Go to **Developer** tab (or the server icon on the left)
5. Click **Start Server**. It should say something like `Server running on http://localhost:1234`
6. Make sure **CORS** is enabled if you're hitting it from a browser later

## 4. Run the agent

```bash
export LMSTUDIO_URL=http://localhost:1234/v1
export PAPERS_DIR=/tmp/papers
export PYTHONPATH=$(pwd)

uv run uvicorn agent.app:app --reload --port 8000
```

You should see uvicorn start up. Leave this terminal running.

## 5. Fire the triage

Open another terminal:

```bash
curl -X POST http://localhost:8000/triage \
  -H "Content-Type: application/json" \
  -d '{"papers_dir": "/tmp/papers"}'
```

This will take a while depending on your hardware — the model needs to read all the paper texts and produce structured JSON output. On a 4090 with a 70B Q4 model, expect 30-90 seconds depending on the number of papers.

## 6. Check results

```bash
# what ended up where
ls /tmp/papers/must-read/
ls /tmp/papers/nice-to-read/
ls /tmp/papers/bullshit/

# reading order
cat /tmp/papers/reading_order.txt

# full report
cat /tmp/papers/triage_report.json | python -m json.tool

# score it against ground truth
PYTHONPATH=$(pwd) uv run python environment/judge.py /tmp/papers environment/ground_truth.json
```
