"""Build the standalone interactive page (app/web/field_shift.html) from data/processed/.

The page carries the same precomputed results as the Streamlit app and runs Engine 3's
constraint filter and priority ranking in the browser (ratings are precomputed, so V9
holds by construction). Run from the repo root:  python app/build_web.py
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from app import data as D
from app import takeaways as T
from pipeline import engine3 as E3

TEMPLATE = REPO / "app" / "web_template.html"
OUT = REPO / "app" / "web" / "field_shift.html"
SMOOTH_STEP_DAYS = 2


def _field(fid: str, cross: dict) -> dict:
    static, props = D.load_static(fid), D.demo_props().get(fid, {})
    e1, e2, e3 = D.load_engine1(fid), D.load_engine2(fid), D.load_engine3(fid)
    obs, smooth, power = D.load_hls(fid), D.load_smooth(fid), D.load_power(fid)
    soil, terrain = static["soil"], static["terrain"]
    metrics = D.window_metrics(power)
    conds = []
    for col, (title, unit, src) in D.METRICS.items():
        band = D.baseline_band(metrics, col)
        conds.append({
            "key": col, "title": title, "unit": unit, "source": src,
            "values": [round(float(v), 3) for v in metrics[col]],
            "band": [round(band["p20"], 3), round(band["p80"], 3)],
            "trend": round(D.trend_per_decade(metrics, col), 3),
            "p": round(D.trend_pvalue(metrics, col), 3),
        })
    passes = len(obs)
    o = obs[obs["ndvi_median"].notna()].sort_values("date")
    sm = smooth.iloc[::SMOOTH_STEP_DAYS]
    return {
        "id": fid, "letter": fid.split("_")[-1].upper(), "county": props.get("county", ""), "corn_years": props.get("corn_years", ""),
        "naip_note": props.get("naip_note", ""), "area": static["area_ha"]["value"], "passes": passes, "interior_px": static["interior_pixels_approx"]["value"],
        "slope": terrain["mean_slope_pct"]["value"], "lidar": terrain["ref_3dep_10m_pct"]["value"],
        "soil": {"muname": soil["muname"]["value"], "drainage": soil["drclassdcd"]["value"], "aws": soil["aws0100wta"]["value"],
                 "om": soil["om_r"]["value"], "kfact": soil["kwfact"]["value"], "slope_class": soil["slopegradwta"]["value"]},
        "crops": [{"y": int(r["dates"]), "crop": r["value"], "share": r.get("share")} for r in static["crop_sequence"]],
        "e1": {"summary": e1["summary"], "sensitivity": e1["sensitivity_no_living_cover_months"], "coverage": D.coverage_text(e1),
               "threshold": e1["method"]["cover_threshold_ndvi"], "seasons": e1["seasons"]},
        "e2": {"summary": e2["summary"], "seasons": e2["seasons"], "source": e2["source"]},
        "e3": {k: e3[k] for k in ("ratings", "notes", "not_established", "sources", "erosion_importance", "current_no_living_cover_months", "cover_effect")},
        "obs": {"d": o["date"].dt.strftime("%Y-%m-%d").tolist(), "s": [s[0] for s in o["sensor"]], "v": [round(float(v), 3) for v in o["ndvi_median"]],
                "n": o["n_valid"].astype(int).tolist(), "k": [int(b) for b in o["passes_v1"]]},
        "smooth": {"start": sm.index[0].strftime("%Y-%m-%d"), "step": SMOOTH_STEP_DAYS, "v": [round(float(v), 3) for v in sm.to_numpy()]},
        "conditions": {"years": [int(y) for y in metrics.index], "metrics": conds},
        "heads": T.headlines(e1, e2, cross, fid.split("_")[-1].upper()),
        "actions": T.field_actions(e1, e2, e3, cross),
        "trend_msg": T.trend_message([{"title": c["title"], "unit": c["unit"], "slope": c["trend"], "p": c["p"]} for c in conds],
                                     e2["summary"]["all_seasons"]["stress_seasons"], e2["summary"]["all_seasons"]["seasons"]),
    }


def build() -> Path:
    cross = T.cross_fields([(f.split("_")[-1].upper(), D.load_engine1(f), D.load_engine2(f)) for f in D.field_ids()])
    data = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "fields": [_field(fid, cross) for fid in D.field_ids()],
        "cross": cross,
        "decision": T.DECISION,
        "validation": T.validation_summary(),
        "engine3": {
            "PRIORITIES": E3.PRIORITIES, "CRITERIA": E3.CRITERIA, "CRITERIA_FOR_PRIORITY": E3.CRITERIA_FOR_PRIORITY,
            "CANDIDATES": [{"id": c["id"], "name": c["name"], "needs": sorted(c["needs"])} for c in E3.CANDIDATES],
            "CONSTRAINTS": E3.CONSTRAINTS,
        },
    }
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html)
    return OUT


if __name__ == "__main__":
    p = build()
    print(f"wrote {p.relative_to(REPO)} ({p.stat().st_size / 1024:.0f} KB)")
