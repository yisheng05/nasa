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
    assert "keeping the current rotation comes out on top" in T.priority_action(e3, ["Workload and simplicity"], set())["text"]
    soil = T.priority_action(e3, ["Soil protection"], set())["text"]
    assert "adding oats + red clover comes out on top" in soil and "adding a cereal rye cover does instead" in soil
    no_oats = T.priority_action(e3, ["Soil protection"], {"small_grain_market"})["text"]
    assert "adding a cereal rye cover comes out on top." in no_oats and "instead" not in no_oats
    assert T.priority_action(e3, [], set())["text"].startswith("Set your priorities")


def test_stability_line():
    from pipeline import engine3 as E3

    e3 = _docs("field_a")[2]
    kept, _ = E3.apply_constraints(set())
    assert T.stability_line(e3["ratings"], kept, ["Soil protection"]) == (
        "Oats + red clover comes out on top unless workload and simplicity comes first, when keeping the current rotation does.")
    only, _ = E3.apply_constraints({"small_grain_market", "cover_termination"})
    assert T.stability_line(e3["ratings"], only, ["Soil protection"]).startswith("Only the current rotation is left")


def test_trend_message_reports_significance_honestly():
    flat = [{"title": "Daily maximum temperature, 15 Jun–15 Aug mean", "unit": "°C", "slope": 0.22, "p": 0.37},
            {"title": "Days above 30 °C, 15 Jun–15 Aug", "unit": "days", "slope": 1.4, "p": 0.38},
            {"title": "Rainfall, 15 Jun–15 Aug", "unit": "mm", "slope": -5.9, "p": 0.62}]
    m = T.trend_message(flat, 4, 10)
    assert m["title"] == "Is it changing? Not clearly, yet" and "not statistically significant" not in m["title"]
    assert "p ≥ 0.37" in m["text"] and "4 of 10 seasons" in m["text"]
    sig = [dict(flat[0], p=0.01), *flat[1:]]
    assert T.trend_message(sig, 4, 10)["title"].startswith("Is it changing? Yes")


def test_validation_summary_reads_the_validation_files():
    lines = T.validation_summary()
    assert any("MSLSP30NA" in x for x in lines) and any("Crop Progress" in x for x in lines)
    assert any("rated blind by AI" in x for x in lines)


def test_what_worked_follows_the_evidence():
    w = T.what_worked([(L, *_docs(f)[:2]) for L, f in FIELDS])
    by = {p["letter"]: p for p in w["fields"]}
    for L, f in FIELDS:
        e2 = _docs(f)[1]
        flagged = [s for s in e2["seasons"] if s["stress_flag"]]
        assert by[L]["flagged"] == len(flagged)
        assert by[L]["held"] == sum(s["vigour"] in ("similar", "above") for s in flagged)
        assert {d["season"] for d in by[L]["dips"]} == {s["season"] for s in e2["seasons"] if not s["stress_flag"] and s["vigour"] == "below"}
    assert by["C"]["cover"] is None and "No green after harvest" in by["C"]["lines"][0]
    b = by["B"]["cover"]
    assert b["with_years"] == [2018, 2022, 2024] and b["diff"] > 1.5  # the field that greens after harvest has much less bare soil after it
    assert "12 of 13" in w["lead"] and "not yield" in w["caveat"]


def test_dips_cite_their_evidence():
    a = T.field_worked("A", *_docs("field_a")[:2])
    d2020 = next(d for d in a["dips"] if d["season"] == 2020)
    assert any("Drought Monitor" in x for x in d2020["why"])
