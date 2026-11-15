"""Farmer-facing messages come from the evidence JSON and say what the evidence says (V8)."""

import json
from pathlib import Path

from app import takeaways as T

P = Path(__file__).resolve().parent.parent / "data" / "processed"
FIELDS = [("A", "field_a"), ("B", "field_b"), ("C", "field_c")]


def _docs(fid):
    return [json.loads((P / fid / f"engine{i}.json").read_text()) for i in (1, 2, 3)]


def _cross():
    return T.cross_fields([(L, *_docs(f)[:2]) for L, f in FIELDS])


def test_cross_fields_matches_engines():
    cx = _cross()
    for g, (_, f) in zip(cx["green"], FIELDS, strict=True):
        e1 = _docs(f)[0]
        assert g["count"] == sum(1 for s in e1["seasons"] if s["crop"] == "corn" and (s.get("autumn_green_obs") or 0) >= 2)
    for h, (_, f) in zip(cx["hits"], FIELDS, strict=True):
        flagged = {s["season"]: s["crop"] for s in _docs(f)[1]["seasons"] if s["stress_flag"]}
        assert {y: c for y, c in zip(cx["years"], h["cells"], strict=True) if c} == flagged


def test_window_span_is_calendar_days():
    e2 = _docs("field_a")[1]
    w0, w1 = T.window_span(e2)
    starts = sorted(s["window_start"][5:] for s in e2["seasons"] if s["window_start"])
    assert w0.endswith(("June", "July")) and starts[0] in ("06-29",)  # earliest start by day, not by year
    assert w1.endswith("September")


def test_actions_quote_the_evidence():
    cx = _cross()
    for _, f in FIELDS:
        e1, e2, e3 = _docs(f)
        acts = T.actions(e1, e2, e3, cx, ["Soil protection"], set())
        assert [a["title"] for a in acts][:3] == ["Cover the gap", "Treat weather risk as a calendar problem", "Decide by your first priority"]
        assert f"about {e1['summary']['no_living_cover_months_per_year']} months" in acts[0]["text"]
        a = e2["summary"]["all_seasons"]
        assert f"{a['stress_seasons']} of {a['seasons']} seasons" in acts[1]["text"]


def test_priority_action_follows_the_ranking():
    e3 = _docs("field_a")[2]
    assert "Corn–soybean (current) ranks first" in T.priority_action(e3, ["Workload and simplicity"], set())["text"]
    soil = T.priority_action(e3, ["Soil protection"], set())["text"]
    assert "oats/red clover ranks first" in soil and "cereal rye cover ranks first instead" in soil
    no_oats = T.priority_action(e3, ["Soil protection"], {"small_grain_market"})["text"]
    assert "cereal rye cover ranks first." in no_oats and "instead" not in no_oats
    assert T.priority_action(e3, [], set())["text"].startswith("Set your priorities")
