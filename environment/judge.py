"""
Scoring for the paper triage environment.

Weights:
  classification accuracy   40%
  reading_order format      10%
  ranking correlation       25%
  report schema valid       10%
  keyword overlap           15%

Output: 0–100
"""
import json, os, sys
from scipy.stats import kendalltau

STOP_WORDS = frozenset(
    "the a an and or of in for to is are that with on by as it its this".split()
)

def _load_gt(path):
    with open(path) as f:
        return json.load(f)


def score_classification(base_dir, gt_labels):
    n = len(gt_labels)
    if n == 0:
        return 0.0
    hits = sum(
        os.path.isfile(os.path.join(base_dir, m["classification"], fn))
        for fn, m in gt_labels.items()
    )
    return hits / n


def parse_reading_order(base_dir):
    """returns (is_valid, [filenames])"""
    ro_path = os.path.join(base_dir, "reading_order.txt")
    if not os.path.isfile(ro_path):
        return False, []
    with open(ro_path) as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    fnames = []
    for ln in lines:
        # "1. foo.pdf | some reason"
        try:
            after_dot = ln.split(".", 1)[1].strip()
            name = after_dot.split("|")[0].strip()
            if name.endswith(".pdf"):
                fnames.append(name)
        except (IndexError, ValueError):
            pass
    return len(fnames) > 0, fnames


def score_ranking(predicted, reference):
    if not predicted or not reference:
        return 0.0
    common = [p for p in reference if p in predicted]
    if len(common) < 2:
        return 0.5 if len(common) == 1 else 0.0

    ref_r = {p: i for i, p in enumerate(reference)}
    pred_r = {p: i for i, p in enumerate(predicted)}
    tau, _ = kendalltau(
        [ref_r[p] for p in common],
        [pred_r[p] for p in common],
    )
    return (tau + 1.0) / 2.0


def score_report_schema(base_dir, n_expected):
    path = os.path.join(base_dir, "triage_report.json")
    if not os.path.isfile(path):
        return 0.0
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return 0.0
    if not isinstance(data, list):
        return 0.0

    need = {"filename", "title", "classification", "domain_tags",
            "key_contribution", "relevance_score"}
    ok_cls = {"must-read", "nice-to-read", "bullshit"}
    good = 0
    for entry in data:
        if not isinstance(entry, dict):
            continue
        if not need.issubset(entry):
            continue
        if entry["classification"] not in ok_cls:
            continue
        tags = entry["domain_tags"]
        if not isinstance(tags, list) or not tags:
            continue
        rs = entry["relevance_score"]
        if not isinstance(rs, (int, float)) or not (0 <= rs <= 1):
            continue
        good += 1
    return good / n_expected if n_expected else 0.0


def score_keywords(base_dir, gt_labels):
    path = os.path.join(base_dir, "triage_report.json")
    if not os.path.isfile(path):
        return 0.0
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return 0.0
    if not isinstance(data, list):
        return 0.0

    by_name = {}
    for e in data:
        if isinstance(e, dict) and "filename" in e:
            by_name[e["filename"]] = e

    scores = []
    for fn, meta in gt_labels.items():
        if fn not in by_name:
            scores.append(0.0)
            continue
        gt_w = set(meta["key_contribution"].lower().split()) - STOP_WORDS
        pred_w = set(by_name[fn].get("key_contribution", "").lower().split()) - STOP_WORDS
        if not gt_w:
            scores.append(0.0)
            continue
        scores.append(len(gt_w & pred_w) / len(gt_w))

    return sum(scores) / len(scores) if scores else 0.0


def judge(base_dir, gt_path):
    gt = _load_gt(gt_path)
    labels = gt["labels"]
    ref_rank = gt["reference_ranking"]
    n = len(labels)

    c = score_classification(base_dir, labels)
    ro_ok, pred_order = parse_reading_order(base_dir)
    r = score_ranking(pred_order, ref_rank)
    s = score_report_schema(base_dir, n)
    k = score_keywords(base_dir, labels)

    total = (0.40*c + 0.10*(1.0 if ro_ok else 0.0) + 0.25*r + 0.10*s + 0.15*k) * 100

    return {
        "score": round(total, 2),
        "breakdown": {
            "classification_accuracy": round(c, 3),
            "reading_order_format": 1.0 if ro_ok else 0.0,
            "ranking_correlation": round(r, 3),
            "report_schema": round(s, 3),
            "keyword_overlap": round(k, 3),
        },
    }


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else "/papers"
    gt = sys.argv[2] if len(sys.argv) > 2 else "/environment/ground_truth.json"
    print(json.dumps(judge(base, gt), indent=2))
