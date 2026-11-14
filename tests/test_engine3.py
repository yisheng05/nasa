"""Engine 3: rule outputs, constraints, priority ordering (V9), determinism (V7), evidence on every cell (V8 groundwork)."""

import itertools

import pytest

from pipeline import engine3 as E3


def _static(slope=1.6, p90=2.8, s_slope=1.6, k=0.27):
    return {
        "soil": {"slopegradwta": {"value": s_slope}, "kwfact": {"value": k}},
        "terrain": {"mean_slope_pct": {"value": slope}, "p90_slope_pct": {"value": p90}},
    }


def _e1(shares, off_days, autumn=0):
    seasons = [
        {"season": 2016 + i, "crop": "corn" if i % 2 == 0 else "soybeans", "cover_year_partial": i == 0,
         "no_living_cover_share": sh, "off_season_living_days": od}
        for i, (sh, od) in enumerate(zip(shares, off_days, strict=True))
    ]
    months = round(sum(s["no_living_cover_share"] for s in seasons[1:]) / (len(seasons) - 1) * 12, 1)
    return {"seasons": seasons, "summary": {"no_living_cover_months_per_year": months, "autumn_green_seasons": autumn}}


def _e2(k=4, n=10, expected=2.8):
    return {"summary": {"all_seasons": {"stress_seasons": k, "seasons": n, "expected_stress_seasons": expected}}}


SHARES = [0.6, 0.72, 0.74, 0.75, 0.73, 0.74]
NO_COVER = [0, 0, 0, 0, 0, 0]


def test_observed_cover_effect_within_crop():
    plain = _e1(SHARES, NO_COVER)
    covered = _e1([0.6, 0.56, 0.74, 0.58, 0.73, 0.57], [0, 60, 0, 55, 0, 50])
    eff = E3.observed_cover_effect({"a": plain, "b": covered})
    assert eff is not None
    assert eff["share_reduction"] == pytest.approx(0.73 - 0.57, abs=0.02)
    assert E3.observed_cover_effect({"a": plain}) is None


def test_ratings_have_evidence_and_confidence():
    eff = {"share_reduction": 0.14, "months_per_year": 1.7}
    r = E3.rate_field(_static(), _e1(SHARES, NO_COVER), _e2(), eff)
    for c in E3.CANDIDATES:
        for k in E3.CRITERIA:
            cell = r["ratings"][c["id"]][k]
            assert cell["rating"] in ("baseline", "better", "similar", "worse")
            assert cell["evidence"] and cell["confidence"]
    assert r["ratings"]["cs_rye"]["Soil cover and living roots"]["rating"] == "better"
    assert r["ratings"]["cs_rye"]["Workload and complexity"]["rating"] == "worse"
    assert r["ratings"]["cso_rc"]["Nitrogen needs"]["rating"] == "better"


def test_erosion_importance_from_slope():
    eff = {"share_reduction": 0.14, "months_per_year": 1.7}
    assert E3.rate_field(_static(), _e1(SHARES, NO_COVER), _e2(), eff)["erosion_importance"] == "lower"
    assert E3.rate_field(_static(s_slope=3.2), _e1(SHARES, NO_COVER), _e2(), eff)["erosion_importance"] == "higher"


def test_existing_cover_reduces_rye_gain_and_is_noted():
    eff = {"share_reduction": 0.14, "months_per_year": 1.7}
    plain = E3.rate_field(_static(), _e1(SHARES, NO_COVER), _e2(), eff)
    covered_e1 = _e1([0.6, 0.56, 0.74, 0.58, 0.73, 0.57], [0, 60, 0, 55, 0, 50], autumn=3)
    covered = E3.rate_field(_static(), covered_e1, _e2(), eff)
    assert covered["notes"] and "cover crop already" in covered["notes"][0]
    gain = lambda r: float(r["current_no_living_cover_months"]) - float(r["ratings"]["cs_rye"]["Soil cover and living roots"]["estimate"].split("~")[1].split(" ")[0])
    assert gain(covered) < gain(plain)


def test_constraints_drop_candidates():
    kept, dropped = E3.apply_constraints({"small_grain_market"})
    assert [c["id"] for c in kept] == ["cs", "cs_rye"]
    assert dropped[0][0].startswith("Corn–soybean–oats")
    kept, _ = E3.apply_constraints({"small_grain_market", "cover_termination"})
    assert [c["id"] for c in kept] == ["cs"]


def test_v9_priorities_reorder_but_never_change_ratings():
    eff = {"share_reduction": 0.14, "months_per_year": 1.7}
    r = E3.rate_field(_static(), _e1(SHARES, NO_COVER), _e2(), eff)
    snapshot = {cid: {k: v["rating"] for k, v in crit.items()} for cid, crit in r["ratings"].items()}
    kept, _ = E3.apply_constraints(set())
    tops = set()
    for perm in itertools.permutations(E3.PRIORITIES):
        order = E3.rank(r["ratings"], kept, list(perm))
        tops.add(order[0]["id"])
        assert {cid: {k: v["rating"] for k, v in crit.items()} for cid, crit in r["ratings"].items()} == snapshot
    assert len(tops) > 1  # the ranking does respond to priorities
    assert E3.rank(r["ratings"], kept, ["Workload and simplicity"])[0]["id"] == "cs"
    assert E3.rank(r["ratings"], kept, ["Soil protection"])[0]["id"] != "cs"


def test_v7_deterministic():
    eff = {"share_reduction": 0.14, "months_per_year": 1.7}
    a = E3.rate_field(_static(), _e1(SHARES, NO_COVER), _e2(), eff)
    b = E3.rate_field(_static(), _e1(SHARES, NO_COVER), _e2(), eff)
    assert a == b
