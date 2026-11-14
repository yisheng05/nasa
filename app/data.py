"""Read precomputed evidence from data/processed/ and derive display tables.

Pure functions (no Streamlit) so they can be tested. Every derived value keeps
its source label so the UI can show provenance (handoff §12.4, V8).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
PROCESSED = REPO / "data" / "processed"
DEMO_FIELDS = REPO / "pipeline" / "demo_fields.geojson"

POWER_LABEL = "NASA POWER daily, ~0.5° cell (regional)"
GWET_LABEL = "NASA POWER GWETROOT from GMAO MERRA-2 (modelled, regional)"
BASELINE = (1991, 2020)
WINDOW = ((6, 15), (8, 15))  # calendar proxy for the maize sensitive period
HOT_DAY_C = 30.0  # the maize GDD cap (handoff §7.4)

PRIORITIES = [
    "Soil protection",
    "Water and stress risk",
    "Nitrogen and input needs",
    "Workload and simplicity",
    "Crop diversity",
]
CRITERIA_FOR_PRIORITY = {
    "Soil protection": ["Soil cover and living roots", "Erosion protection"],
    "Water and stress risk": ["Water and stress exposure"],
    "Nitrogen and input needs": ["Nitrogen needs"],
    "Workload and simplicity": ["Workload and complexity"],
    "Crop diversity": ["Crop diversity"],
}
CRITERION_EVIDENCE = {
    "Soil cover and living roots": "Observed no-living-cover days per year (Engine 1, HLS 30 m), adjusted by the candidate's practice.",
    "Erosion protection": "Cover rating combined with field slope (NASADEM, smoothed; V12) and SSURGO slope class.",
    "Water and stress exposure": "Overlap of each crop's sensitive stage with this field's recurring stress window (Engine 2).",
    "Nitrogen needs": "Legume credits in the sequence (crop catalogue, extension sources).",
    "Crop diversity": "Number of distinct crops and functional groups in the rotation.",
    "Workload and complexity": "Qualitative, from equipment and practices the farmer confirms.",
}
CANDIDATES = [
    {"name": "Corn–soybean (current)", "needs": set()},
    {"name": "Corn–soybean + cereal rye cover", "needs": {"cover_termination"}},
    {"name": "Corn–soybean–oats/clover", "needs": {"small_grain_market"}},
]
CONSTRAINTS = {
    "small_grain_market": "No local market for small grains (oats)",
    "cover_termination": "Can't manage spring termination of a cover crop",
}
LONG_TERM_NOTE = "Rented land on a short lease"

CROP_OPTIONS = ["corn", "soybeans", "oats", "alfalfa", "winter wheat", "fallow/idle", "other"]


def field_ids() -> list[str]:
    return sorted(p.name for p in PROCESSED.iterdir() if (p / "field_static.json").exists()) if PROCESSED.exists() else []


def demo_props() -> dict[str, dict]:
    fc = json.loads(DEMO_FIELDS.read_text())
    return {f["properties"]["id"]: f["properties"] for f in fc["features"]}


def load_static(fid: str) -> dict:
    return json.loads((PROCESSED / fid / "field_static.json").read_text())


def load_power(fid: str) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / fid / "power_daily.parquet")


def load_hls(fid: str) -> pd.DataFrame | None:
    p = PROCESSED / fid / "hls_obs.parquet"
    return pd.read_parquet(p) if p.exists() else None


def field_label(fid: str, static: dict, props: dict) -> str:
    letter = fid.split("_")[-1].upper()
    return f"Field {letter} · {static['area_ha']['value']:.1f} ha · corn {props.get('corn_years', '?')} yrs"


def crop_sequence(static: dict) -> pd.DataFrame:
    rows = [
        {"season": int(r["dates"]), "crop": r["value"], "share": r.get("share"), "source": "CDL"}
        for r in static["crop_sequence"]
    ]
    return pd.DataFrame(rows)


def window_metrics(power: pd.DataFrame, window=WINDOW) -> pd.DataFrame:
    """Per-year metrics over a fixed calendar window (regional POWER data)."""
    (m0, d0), (m1, d1) = window
    md = power.index.month * 100 + power.index.day
    w = power[(md >= m0 * 100 + d0) & (md <= m1 * 100 + d1)]
    g = w.groupby(w.index.year)
    out = pd.DataFrame(
        {
            "rain_mm": g["PRECTOTCORR"].sum(),
            "gwetroot": g["GWETROOT"].mean(),
            "tmax_c": g["T2M_MAX"].mean(),
            "hot_days": g["T2M_MAX"].apply(lambda s: int((s > HOT_DAY_C).sum())),
        }
    )
    out.index.name = "year"
    return out


METRICS = {
    "rain_mm": ("Rainfall, 15 Jun–15 Aug", "mm", POWER_LABEL),
    "gwetroot": ("Root-zone wetness, 15 Jun–15 Aug mean", "0–1 index", GWET_LABEL),
    "tmax_c": ("Daily maximum temperature, 15 Jun–15 Aug mean", "°C", POWER_LABEL),
    "hot_days": (f"Days above {HOT_DAY_C:.0f} °C, 15 Jun–15 Aug", "days", POWER_LABEL),
}


def baseline_band(metrics: pd.DataFrame, col: str, years=BASELINE) -> dict:
    b = metrics.loc[years[0] : years[1], col]
    return {"p20": float(b.quantile(0.2)), "median": float(b.median()), "p80": float(b.quantile(0.8))}


def percentile_vs_baseline(value: float, metrics: pd.DataFrame, col: str, years=BASELINE) -> float:
    b = metrics.loc[years[0] : years[1], col].to_numpy()
    return float((b <= value).mean() * 100)


def trend_per_decade(metrics: pd.DataFrame, col: str) -> float:
    s = metrics[col].dropna()
    slope = np.polyfit(s.index.to_numpy(dtype=float), s.to_numpy(dtype=float), 1)[0]
    return float(slope * 10)


def corn_season_context(metrics: pd.DataFrame, seq: pd.DataFrame) -> pd.DataFrame:
    """Each corn season's window rainfall and root-zone wetness as a percentile of 1991–2020."""
    corn = seq.loc[seq.crop == "corn", "season"].tolist()
    rows = []
    for y in corn:
        if y not in metrics.index:
            continue
        rows.append(
            {
                "season": y,
                "rain_mm": round(float(metrics.at[y, "rain_mm"]), 0),
                "rain_pctile": round(percentile_vs_baseline(metrics.at[y, "rain_mm"], metrics, "rain_mm")),
                "gwetroot": round(float(metrics.at[y, "gwetroot"]), 2),
                "gwetroot_pctile": round(percentile_vs_baseline(metrics.at[y, "gwetroot"], metrics, "gwetroot")),
                "hot_days": int(metrics.at[y, "hot_days"]),
            }
        )
    return pd.DataFrame(rows)


def ordered_criteria(priority_order: list[str]) -> list[str]:
    seen, out = set(), []
    for p in priority_order + [p for p in PRIORITIES if p not in priority_order]:
        for c in CRITERIA_FOR_PRIORITY[p]:
            if c not in seen:
                seen.add(c)
                out.append(c)
    return out


def apply_constraints(active: set[str]) -> tuple[list[dict], list[tuple[str, str]]]:
    """Engine 3 step 1: drop candidates that break a stated hard constraint."""
    kept, dropped = [], []
    for c in CANDIDATES:
        hit = c["needs"] & active
        if hit:
            dropped.append((c["name"], "; ".join(CONSTRAINTS[h] for h in sorted(hit))))
        else:
            kept.append(c)
    return kept, dropped
