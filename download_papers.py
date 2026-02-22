"""Download papers from papers.json into the inbox and generate ground_truth.json.

Usage:
    uv run python download_papers.py
    uv run python download_papers.py --inbox /tmp/papers/inbox
    uv run python download_papers.py papers.json --inbox /tmp/papers/inbox

Category-to-classification mapping:
    "AI and RL (2026)"  -> must-read
    "MLOps"             -> nice-to-read
    everything else     -> bullshit
"""

import json
import re
import sys
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

CATEGORY_MAP = {
    "AI and RL (2026)": {
        "classification": "must-read",
        "tags": ["reinforcement-learning", "rlhf", "alignment"],
        "relevance": 0.90,
    },
    "MLOps": {
        "classification": "nice-to-read",
        "tags": ["mlops", "ml-engineering", "deployment"],
        "relevance": 0.55,
    },
}

BULLSHIT_DEFAULT = {
    "classification": "bullshit",
    "tags": ["off-topic"],
    "relevance": 0.10,
}


def arxiv_id_from_url(url: str) -> str | None:
    # new-style: 2601.21268, 2601.21268v2
    m = re.search(r'arxiv\.org/(?:abs|pdf)/(\d+\.\d+(?:v\d+)?)', url)
    if m:
        return m.group(1)
    # old-style: cond-mat/0410483, hep-ph/9905221v1
    m = re.search(r'arxiv\.org/(?:abs|pdf)/([\w.-]+/\d+(?:v\d+)?)', url)
    if m:
        return m.group(1)
    return None


def url_to_pdf(url: str) -> str:
    arxiv_id = arxiv_id_from_url(url)
    if arxiv_id:
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return url


def url_to_filename(url: str, title: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')[:60]
    return f"{slug}.pdf"


def download(url: str, dest: Path, timeout: int = 60) -> bool:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            if not content[:5].startswith(b'%PDF'):
                print(f"  WARNING: response doesn't look like a PDF ({content[:20]!r})")
                return False
            dest.write_bytes(content)
            return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"  ERROR: {e}")
        return False


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "papers.json"
    papers_dir = Path(os.environ.get("PAPERS_DIR", "/tmp/papers"))
    inbox = papers_dir / "inbox"

    if "--inbox" in sys.argv:
        idx = sys.argv.index("--inbox")
        inbox = Path(sys.argv[idx + 1])
        papers_dir = inbox.parent

    with open(json_path) as f:
        data = json.load(f)

    papers = data["arxiv_papers"]

    # Create directories
    inbox.mkdir(parents=True, exist_ok=True)
    for folder in ["must-read", "nice-to-read", "bullshit"]:
        (papers_dir / folder).mkdir(parents=True, exist_ok=True)

    # Build ground truth as we download
    labels = {}
    must_reads = []

    total = len(papers)
    downloaded = 0
    failed = 0
    skipped = 0

    print(f"Downloading {total} papers into {inbox}\n")

    for paper in papers:
        url = paper["url"]
        title = paper["title"]
        category = paper["category"]
        info = CATEGORY_MAP.get(category, BULLSHIT_DEFAULT)
        classification = info["classification"]

        pdf_url = url_to_pdf(url)
        filename = url_to_filename(url, title)
        dest = inbox / filename

        if dest.exists():
            print(f"  {filename} — already exists, skipping")
            skipped += 1
        else:
            print(f"  [{classification:>12}] {filename}")
            print(f"               <- {pdf_url}")
            if download(pdf_url, dest):
                downloaded += 1
            else:
                failed += 1

            # Rate-limit for arxiv
            if 'arxiv.org' in pdf_url:
                time.sleep(3)

        # Add to ground truth regardless of download success (for format)
        labels[filename] = {
            "classification": classification,
            "title": title,
            "domain_tags": info["tags"],
            "key_contribution": title,
            "relevance_score": info["relevance"],
        }

        if classification == "must-read":
            must_reads.append(filename)

    ground_truth = {
        "labels": labels,
        "reference_ranking": must_reads,
    }

    gt_path = Path("environment/ground_truth.json")
    gt_path.write_text(json.dumps(ground_truth, indent=2) + "\n")
    print(f"\nGround truth written to {gt_path}")
    print(f"  {sum(1 for v in labels.values() if v['classification'] == 'must-read')} must-read, "
          f"{sum(1 for v in labels.values() if v['classification'] == 'nice-to-read')} nice-to-read, "
          f"{sum(1 for v in labels.values() if v['classification'] == 'bullshit')} bullshit")

    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
