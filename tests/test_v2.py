"""Field Shift V2: the model follows the engines, and the page's live logic matches the model."""

import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app import data as D
from app import v2_model as V
from pipeline import engine3 as E3

PAGE = Path(__file__).resolve().parent.parent / "app" / "web" / "field_shift_v2.html"


@pytest.fixture(scope="module")
def model():
    return V.build()


def test_cover_effect_matches_engine3(model):
    e1 = {f: D.load_engine1(f) for f in D.field_ids()}
    ref = E3.observed_cover_effect(e1)
    assert model["effect"]["share_reduction"] == ref["share_reduction"]
    assert model["effect"]["months_per_year"] == ref["months_per_year"]


def test_estimates_match_v1_rye_estimates(model):
    for f in D.field_ids():
        est = D.load_engine3(f)["ratings"]["cs_rye"]["Soil cover and living roots"]["estimate"]
        v1 = float(re.search(r"~([\d.]+) months", est).group(1))
        L = f[-1].upper()
        assert V.estimate_months(model["cover_rows"], L, model["effect"]) == v1


def test_farmer_answers_change_the_effect(model):
    rows = model["cover_rows"]
    full = V.cover_effect(rows)
    some = V.cover_effect(rows, frozenset({("B", 2018), ("B", 2022)}))
    none = V.cover_effect(rows, frozenset({("A", 2017), ("B", 2018), ("B", 2022), ("B", 2024)}))
    assert some["months_per_year"] < full["months_per_year"] and len(some["cover_years"]) == 2
    assert none is None and V.estimate_months(rows, "A", none) is None


def test_exposure_is_measured_and_supports_the_water_rating(model):
    for L, f in model["fields"].items():
        ex = f["exposure"]
        assert ex["hottest"]["start"].startswith("07"), L  # the hottest half-month falls in July here
        assert ex["crops"]["oats"]["wetness"] > ex["options"]["cs"]["wetness"]
        r = f["ratings"]["cso_rc"]["Water and stress exposure"]
        assert r["rating"] == "better" and f"{ex['crops']['oats']['wetness']:.2f}" in r["evidence"]
        assert ex["options"]["cso_rc"]["years_in_hottest"] == 2 and ex["options"]["cso_rc"]["rotation_years"] == 3


def test_where_to_start_and_plans(model):
    assert model["start"]["cs_rye"]["field"] == max(model["gains"], key=model["gains"].get)
    for o in ("cs_rye", "cso_rc"):
        for f in model["farm"]:
            plan = model["plans"][o][f["letter"]]
            assert any(f"Field {f['letter']}" in s["what"] for s in plan["steps"]) and plan["checks"]
    rye_c = model["plans"]["cs_rye"]["C"]["steps"]
    assert any("ahead of soybeans" in s["what"] for s in rye_c)


def test_calendar_rows_cover_the_year(model):
    for f in model["fields"].values():
        for rows in f["calendar"].values():
            for r in rows:
                segs = r["segments"]
                assert segs[0]["start"] == 1 and segs[-1]["end"] == 365
                assert all(a["end"] + 1 == b["start"] for a, b in itertools.pairwise(segs))


@pytest.mark.skipif(shutil.which("node") is None or not PAGE.exists(), reason="needs node and a built page (python app/build_v2.py)")
def test_page_logic_matches_model(tmp_path, model):
    html = PAGE.read_text()
    assert "/*__" not in html
    data = json.loads(re.search(r"const DATA = (\{.*?\});\nconst E3", html, re.DOTALL).group(1))
    logic = re.search(r"/\* -+ V2 logic.*?\*/(.*?)/\* -+ end of V2 logic", html, re.DOTALL).group(1)
    years = [("A", 2017), ("B", 2018), ("B", 2022), ("B", 2024)]
    cases = []
    for k in range(len(years) + 1):
        for ex in itertools.combinations(years, k):
            eff = V.cover_effect(model["cover_rows"], frozenset(ex))
            est = {f["letter"]: V.estimate_months(model["cover_rows"], f["letter"], eff) for f in model["farm"]}
            gains = {L: (round(next(f["bare_months"] for f in model["farm"] if f["letter"] == L) - e, 1) if e is not None else None) for L, e in est.items()}
            start = {o: (s["field"] if (s := V.where_to_start(o, model["farm"], gains)) else None) for o in ("cs_rye", "cso_rc")}
            soil = {f["letter"]: V.rye_soil_rating(f["bare_months"], est[f["letter"]], eff) for f in model["farm"]}
            cases.append({"ex": [f"{a}-{b}" for a, b in ex], "eff": eff, "est": est, "start": start, "soil": soil})
    script = tmp_path / "v2parity.js"
    script.write_text(
        "const E3=" + json.dumps(data["engine3"]) + ";const DATA=" + json.dumps({"farm": data["farm"], "cover_rows": data["cover_rows"]}) + ";\n" + logic
        + "\nconst cases=" + json.dumps(cases, default=list) + ";let bad=[];for(const c of cases){const ex=new Set(c.ex);const e=coverEffect(DATA.cover_rows,ex);"
        "const est={},gains={};DATA.farm.forEach(f=>{est[f.letter]=estimateMonths(DATA.cover_rows,f.letter,e);gains[f.letter]=est[f.letter]==null?null:round1(f.bare_months-est[f.letter]);});"
        "const start={cs_rye:whereToStart('cs_rye',DATA.farm,gains),cso_rc:whereToStart('cso_rc',DATA.farm,gains)};"
        "const soil={};DATA.farm.forEach(f=>{soil[f.letter]=ryeSoilRating(f.bare_months,est[f.letter],e);});"
        "const ce=c.eff?{share_reduction:c.eff.share_reduction,months_per_year:c.eff.months_per_year,cover_years:c.eff.cover_years}:null;"
        "if(JSON.stringify(e)!==JSON.stringify(ce)||JSON.stringify(est)!==JSON.stringify(c.est)||JSON.stringify(start)!==JSON.stringify(c.start)||JSON.stringify(soil)!==JSON.stringify(c.soil))bad.push(c.ex);}"
        "console.log(JSON.stringify(bad));"
    )
    out = subprocess.run(["node", str(script)], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "[]", out


def test_plan_follows_each_fields_rotation(model):
    """Rye is sown after a corn harvest so it precedes soybeans; oats follow soybeans (if the alternation continued in 2026)."""
    for f in model["farm"]:
        rye, oats = model["plans"]["cs_rye"][f["letter"]], model["plans"]["cso_rc"][f["letter"]]
        assert rye["start_year"] == (2027 if f["corn_parity"] == 1 else 2028)
        assert oats["start_year"] == (2027 if f["crop_2026"] == "soybeans" else 2028)
        assert all(f"Field {g['letter']}" not in s["what"] for s in rye["steps"] + oats["steps"] for g in model["farm"] if g["letter"] != f["letter"])


def test_trend_summary_matches_its_numbers(model):
    for F in model["fields"].values():
        t = F["trend"]
        assert t["since"] == 1981 and set(t["metrics"]) == set(D.METRICS)
        sig = any(v["p"] < 0.05 for v in t["metrics"].values())
        assert t["significant"] == sig
        assert ("None of these trends is statistically significant" in t["text"]) == (not sig)
        assert f"{abs(t['metrics']['tmax_c']['slope']):.1f} °C" in t["text"]


def test_soil_water_is_shown_and_used(model):
    static = {f[-1].upper(): json.loads((D.PROCESSED / f / "field_static.json").read_text()) for f in D.field_ids()}
    for f in model["farm"]:
        assert f["aws"] == round(static[f["letter"]]["soil"]["aws0100wta"]["value"], 1)
        for cid in ("cs_rye", "cso_rc"):
            assert "USDA SSURGO" in model["fields"][f["letter"]]["ratings"][cid]["Water and stress exposure"]["evidence"]
    assert "SSURGO" in model["soil_note"] and f"{min(f['aws'] for f in model['farm']):.1f}" in model["soil_note"]
    html = PAGE.read_text()
    assert 'id="soilnote"' in html and 'id="trendtitle"' in html
