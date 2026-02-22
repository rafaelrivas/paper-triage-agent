import json
import os
import shutil
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from tqdm import tqdm

from agent.schemas import PaperAnalysis, ReadingOrderEntry, TriageResult
from agent.pdf_utils import scan_inbox

# kept this as a big string on purpose — easier to tweak prompts
# inline than loading from a file during dev
SYSTEM_MSG = """\
You are a senior RL engineer specializing in RLHF and preference-based training.
You're triaging a batch of ML papers to decide what's worth your time this week.

For each paper you need to:
- Classify it: must-read, nice-to-read, or bullshit
  - must-read = directly relevant to RLHF, DPO, KTO, reward modeling, preference optimization, alignment
  - nice-to-read = tangentially related, decent background, not urgent
  - bullshit = off-topic garbage, irrelevant to your work, or stuff that wastes your time
- Tag the domain areas
- One-liner about key contribution
- Relevance score 0-1

Then rank the must-reads by priority (most impactful first).

Be ruthless. If a paper has nothing to do with RL or alignment, it's bullshit — don't sugarcoat it.
Only mark must-read for papers you'd actually cancel a meeting to go read.\
"""

# local models have way less context headroom than API
_local = bool(os.environ.get("LMSTUDIO_URL"))
PREVIEW_CHARS  = 100   if _local else 300
PAPER_TEXT_CAP = 1_500 if _local else 10_000

@dataclass
class TriageDeps:
    paper_texts: dict[str, str]  # fname -> text


def _pick_model():
    """
    model priority:
      1. LMSTUDIO_URL  -> local LM Studio (openai-compat)
      2. TRIAGE_MODEL starting with "bedrock:" -> AWS Bedrock
      3. TRIAGE_MODEL with any other pydantic-ai string -> whatever provider that is
      4. default -> anthropic claude sonnet
    """
    # local LM Studio
    lm_url = os.environ.get("LMSTUDIO_URL")
    if lm_url:
        name = os.environ.get("LMSTUDIO_MODEL", "loaded-model")
        return OpenAIModel(name, provider=OpenAIProvider(base_url=lm_url))

    # explicit model string (supports bedrock:, anthropic:, openai:, etc)
    model_str = os.environ.get("TRIAGE_MODEL")
    if model_str:
        return model_str

    return "anthropic:claude-sonnet-4-20250514"


triage_agent = Agent(
    _pick_model(),
    deps_type=TriageDeps,
    output_type=TriageResult,
    instructions=SYSTEM_MSG,
)

@triage_agent.tool
def get_paper_list(ctx: RunContext[TriageDeps]) -> list[str]:
    """list all available paper filenames"""
    return list(ctx.deps.paper_texts.keys())

@triage_agent.tool
def read_paper(ctx: RunContext[TriageDeps], filename: str) -> str:
    """return paper text, truncated to fit context window"""
    t = ctx.deps.paper_texts.get(filename)
    if t is None:
        return f"not found: {filename}"
    if len(t) > PAPER_TEXT_CAP:
        return t[:PAPER_TEXT_CAP] + "\n[truncated]"
    return t


async def run_triage(inbox_dir: str) -> TriageResult:
    papers = scan_inbox(inbox_dir)
    if not papers:
        raise ValueError(f"no pdfs in {inbox_dir}")

    deps = TriageDeps(paper_texts=papers)

    # feed previews upfront so the agent doesn't have to tool-call each one individually
    # just enough to get the title + start of abstract
    msg = f"Triage these {len(papers)} papers:\n\n"
    for fname, txt in papers.items():
        chunk = txt[:PREVIEW_CHARS] if len(txt) > PREVIEW_CHARS else txt
        msg += f"--- {fname} ---\n{chunk}\n\n"
    msg += "Classify all and produce the reading order."

    bar = tqdm(total=len(papers), desc="Triaging papers", unit="paper")
    res = await triage_agent.run(msg, deps=deps)
    bar.update(len(papers))
    bar.close()

    return res.output


def materialize_results(result: TriageResult, base_dir: str):
    """move pdfs to their folders + dump output files"""
    inbox = os.path.join(base_dir, "inbox")

    dst_dirs = {}
    for bucket in ("must-read", "nice-to-read", "bullshit"):
        d = os.path.join(base_dir, bucket)
        os.makedirs(d, exist_ok=True)
        dst_dirs[bucket] = d

    for p in result.papers:
        src = os.path.join(inbox, p.filename)
        target = dst_dirs.get(p.classification)
        if target and os.path.exists(src):
            shutil.move(src, os.path.join(target, p.filename))

    # write reading order
    with open(os.path.join(base_dir, "reading_order.txt"), "w") as fh:
        for e in result.reading_order:
            fh.write(f"{e.rank}. {e.filename} | {e.justification}\n")

    # dump full report
    report_data = [p.model_dump() for p in result.papers]
    with open(os.path.join(base_dir, "triage_report.json"), "w") as fh:
        json.dump(report_data, fh, indent=2)
