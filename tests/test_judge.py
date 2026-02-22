import json, os, sys, tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "environment"))

from judge import (
    score_classification,
    parse_reading_order,
    score_ranking,
    score_report_schema,
    score_keywords,
    judge,
)

GT_PATH = os.path.join(os.path.dirname(__file__), "..", "environment", "ground_truth.json")
with open(GT_PATH) as _f:
    GT = json.load(_f)


@pytest.fixture
def ws():
    with tempfile.TemporaryDirectory() as d:
        for sub in ("inbox", "must-read", "nice-to-read", "bullshit"):
            os.makedirs(os.path.join(d, sub))
        yield d


def _place_correct(ws):
    for fn, m in GT["labels"].items():
        open(os.path.join(ws, m["classification"], fn), "w").close()

def _write_order(ws, order):
    with open(os.path.join(ws, "reading_order.txt"), "w") as f:
        for i, fn in enumerate(order, 1):
            f.write(f"{i}. {fn} | reason\n")

def _write_report(ws, entries):
    with open(os.path.join(ws, "triage_report.json"), "w") as f:
        json.dump(entries, f)

def _full_report_entries():
    return [
        {
            "filename": fn,
            "title": m["title"],
            "classification": m["classification"],
            "domain_tags": m["domain_tags"],
            "key_contribution": m["key_contribution"],
            "relevance_score": m["relevance_score"],
        }
        for fn, m in GT["labels"].items()
    ]


# --- classification ---

class TestClassification:
    def test_all_correct(self, ws):
        _place_correct(ws)
        assert score_classification(ws, GT["labels"]) == 1.0

    def test_everything_in_bullshit(self, ws):
        # dump all papers into bullshit and see what happens
        for fn in GT["labels"]:
            open(os.path.join(ws, "bullshit", fn), "w").close()
        got = score_classification(ws, GT["labels"])
        want = sum(1 for m in GT["labels"].values() if m["classification"] == "bullshit") / len(GT["labels"])
        assert got == pytest.approx(want)

    def test_nothing(self, ws):
        assert score_classification(ws, GT["labels"]) == 0.0


# --- reading order ---

class TestReadingOrder:
    def test_happy_path(self, ws):
        _write_order(ws, GT["reference_ranking"])
        ok, names = parse_reading_order(ws)
        assert ok and names == GT["reference_ranking"]

    def test_no_file(self, ws):
        ok, names = parse_reading_order(ws)
        assert not ok and names == []


# --- ranking ---

class TestRanking:
    def test_same_order(self):
        assert score_ranking(GT["reference_ranking"], GT["reference_ranking"]) == 1.0

    def test_reversed(self):
        rev = list(reversed(GT["reference_ranking"]))
        assert score_ranking(rev, GT["reference_ranking"]) == pytest.approx(0.0, abs=0.01)

    def test_empty(self):
        assert score_ranking([], []) == 0.0

    def test_partial(self):
        # first 3 in order -> still perfect for those 3
        assert score_ranking(GT["reference_ranking"][:3], GT["reference_ranking"]) == 1.0


# --- schema ---

class TestSchema:
    def test_valid(self, ws):
        _write_report(ws, _full_report_entries())
        assert score_report_schema(ws, len(GT["labels"])) == 1.0

    def test_missing_fields(self, ws):
        _write_report(ws, [{"filename": "x.pdf"}])
        assert score_report_schema(ws, 1) == 0.0

    def test_bad_json(self, ws):
        with open(os.path.join(ws, "triage_report.json"), "w") as f:
            f.write("nope{{{")
        assert score_report_schema(ws, 1) == 0.0

    def test_no_file(self, ws):
        assert score_report_schema(ws, 5) == 0.0


# --- keywords ---

class TestKeywords:
    def test_exact_match(self, ws):
        entries = [{"filename": fn, "key_contribution": m["key_contribution"]}
                   for fn, m in GT["labels"].items()]
        _write_report(ws, entries)
        assert score_keywords(ws, GT["labels"]) == 1.0

    def test_garbage(self, ws):
        entries = [{"filename": fn, "key_contribution": "xyzzy plugh"}
                   for fn in GT["labels"]]
        _write_report(ws, entries)
        assert score_keywords(ws, GT["labels"]) < 0.15


# --- end to end ---

class TestJudge:
    def test_perfect(self, ws):
        _place_correct(ws)
        _write_order(ws, GT["reference_ranking"])
        _write_report(ws, _full_report_entries())
        assert judge(ws, GT_PATH)["score"] == 100.0

    def test_nothing_done(self, ws):
        # didn't do shit, should basically get zero
        assert judge(ws, GT_PATH)["score"] < 15
