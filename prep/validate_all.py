"""Re-check every validation test in handoff §15 and write docs/validation_results.md.

    python prep/validate_all.py

Recomputes V1/V2 from the HLS observations, re-runs Engines 1-3 from the stored inputs
and checks the evidence JSON comes back byte-identical (V7), runs the test suite (V9,
V10 and the rest), and collects V3, V4, V6, V11, V12 and V13 from the files the
precompute notebook (and prep/v6_visual_check.py) wrote. Network is needed only if the
Drought Monitor cache is missing.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from pipeline import engine1 as E1
from pipeline import engine2 as E2
from pipeline import engine3 as E3
from pipeline.config import PROCESSED, RAW, SEASONS, USDM_COUNTY_FIPS
from pipeline.sources import smap as smap_src
from pipeline.sources import usdm

FIELDS = ["field_a", "field_b", "field_c"]
OUT = REPO / "docs" / "validation_results.md"


def _canon(x) -> str:
    return json.dumps(json.loads(json.dumps(x, default=str)), sort_keys=True)


def _sha(x) -> str:
    return hashlib.sha256(_canon(x).encode()).hexdigest()[:12]


def v1_v2() -> dict:
    per = {}
    for fid in FIELDS:
        o = pd.read_parquet(PROCESSED / fid / "hls_obs.parquet")
        o["date"] = pd.to_datetime(o["date"])
        aproct = o[o.date.dt.month.between(4, 10) & o.date.dt.year.isin(SEASONS)]
        clear = aproct[aproct.passes_v1].groupby(aproct.date.dt.year).date.nunique()
        dropped = int(((aproct.n_valid > 0) & ~aproct.passes_v1).sum())
        per[fid] = {"min": int(clear.min()), "max": int(clear.max()), "dropped_by_v1": dropped, "seasons": len(clear)}
    return per


def v7() -> dict:
    out = {}
    smap_dirs = sorted((RAW / "appeears").glob("fieldshift_smap_l4_*")) if (RAW / "appeears").exists() else []
    smap = smap_src.load_points(smap_dirs) if smap_dirs else {}
    dm = usdm.fetch(USDM_COUNTY_FIPS)
    e1_docs = {}
    for fid in FIELDS:
        st = json.loads((PROCESSED / fid / "field_static.json").read_text())
        o = pd.read_parquet(PROCESSED / fid / "hls_obs.parquet")
        o["date"] = pd.to_datetime(o["date"])
        crops = {int(d["dates"]): d["value"] for d in st["crop_sequence"]}
        yrs = sorted(set(o.date.dt.year) & set(SEASONS))
        runs = [E1.to_records(E1.run(o, crops, yrs)[0]) for _ in range(2)]
        stored = json.loads((PROCESSED / fid / "engine1.json").read_text())
        e1_docs[fid] = stored
        stored_seasons = [{k: v for k, v in s.items() if k != "source"} for s in stored["seasons"]]  # provenance added at write time
        r = {"engine1": {"repeat": _sha(runs[0]) == _sha(runs[1]), "matches_stored": _canon(runs[0]) == _canon(stored_seasons)}}
        power = pd.read_parquet(PROCESSED / fid / "power_daily.parquet")
        esi_p = PROCESSED / fid / "esi_scenes.parquet"
        esi = pd.read_parquet(esi_p) if esi_p.exists() else None
        e2 = [E2.run(stored["seasons"], power, smap.get(fid), esi, usdm=dm) for _ in range(2)]
        s2 = json.loads((PROCESSED / fid / "engine2.json").read_text())
        recs = [E2.to_records(x[0]) for x in e2]
        r["engine2"] = {"repeat": _sha(recs[0]) == _sha(recs[1]) and _sha(e2[0][1]) == _sha(e2[1][1]),
                        "matches_stored": _canon(recs[0]) == _canon(s2["seasons"]) and _canon(e2[0][1]) == _canon(s2["summary"]),
                        "smap_raw_present": bool(smap)}
        out[fid] = r
    ce = E3.observed_cover_effect(e1_docs)
    for fid in FIELDS:
        st = json.loads((PROCESSED / fid / "field_static.json").read_text())
        e2doc = json.loads((PROCESSED / fid / "engine2.json").read_text())
        res = [E3.rate_field(st, e1_docs[fid], e2doc, ce) for _ in range(2)]
        s3 = json.loads((PROCESSED / fid / "engine3.json").read_text())
        out[fid]["engine3"] = {"repeat": _sha(res[0]) == _sha(res[1]),
                               "matches_stored": all(_canon(res[0][k]) == _canon(s3.get(k)) for k in res[0])}
    return out


def tests() -> str:
    p = subprocess.run([sys.executable, "-m", "pytest", "-q", str(REPO / "tests")], capture_output=True, text=True, cwd=REPO, check=False)
    m = re.search(r"(\d+) passed(?:, (\d+) failed)?", p.stdout)
    return f"{m.group(1)} passed" + (f", {m.group(2)} failed" if m and m.group(2) else "") if m else "pytest did not report"


def _csv(name: str) -> pd.DataFrame | None:
    p = PROCESSED / name
    return pd.read_csv(p) if p.exists() else None


def main() -> None:
    rows = []
    d = v1_v2()
    lo, hi = min(v["min"] for v in d.values()), max(v["max"] for v in d.values())
    rows.append(("V1, V2", "Clear April–October dates per season after cloud masking (≥ 50 valid pixels a date; ≥ 8 dates a season)",
                 f"{lo}–{hi} clear dates per season on every field; {sum(v['dropped_by_v1'] for v in d.values())} partly clear dates dropped by V1", lo >= 8))
    v3 = _csv("v3_mslsp_greenup.csv")
    if v3 is not None:
        k, n = int((v3.diff_days.abs() <= 10).sum()), int(v3.diff_days.notna().sum())
        rows.append(("V3", "Engine 1 green-up vs NASA MSLSP30NA 50PCGI, 2016–2019 (±10 days in ≥ 80%)",
                     f"{k}/{n} within ±10 days; Engine 1 runs early by a median {-v3.diff_days.median():.0f} days (range {v3.diff_days.min():+.0f} to {v3.diff_days.max():+.0f})", k >= 0.8 * n))
    v4 = _csv("v4_silking_check.csv")
    if v4 is not None:
        k, n = int(v4.inside.sum()), len(v4)
        late = v4[~v4.inside]
        rows.append(("V4", "Corn silking estimate inside Iowa's 25–75% silked dates, USDA NASS Crop Progress (≥ 70%)",
                     f"{k}/{n} corn seasons inside; misses: " + ", ".join(f"{r.field[-1].upper()} {r.season} ({r.days_from_50:+d} d from Iowa 50%)" for r in late.itertuples()), k >= 0.7 * n))
    rows.append(("V5", "Crop inferred from phenology vs CDL", "Skipped: CDL used directly, as the handoff allows", None))
    v6 = _csv("v6_visual_calls.csv")
    if v6 is not None:
        rnd = v6[v6.set.str.startswith("random")]
        per = rnd.groupby("field").match.sum()
        bal = v6[~v6.set.str.startswith("random")]
        rows.append(("V6", "Off-season green / not-green call vs true-colour HLS, 10 random dates per field (≥ 9 of 10)",
                     " · ".join(f"{f[-1].upper()} {int(k)}/10" for f, k in per.items())
                     + f"; balanced extra set (Sep–May, 5 green + 5 not green): {int(bal.match.sum())}/{len(bal)}. Rated blind by Claude (AI); team to spot-check", bool((per >= 9).all())))
    v = v7()
    ok = all(all(e["repeat"] and e["matches_stored"] for e in r.values() if isinstance(e, dict)) for r in v.values())
    rows.append(("V7", "Determinism: Engines 1–3 re-run twice from stored inputs",
                 "identical runs, and identical to the committed evidence JSON" if ok else "MISMATCH: " + json.dumps(v), ok))
    rows.append(("V8", "Traceability of UI numbers to evidence JSON",
                 "Front ends read the evidence JSON; the web prototype's ranking matches the Python engine (test). Deck and doc numbers audited by hand on 15 Nov", None))
    t = tests()
    rows.append(("V9, V10", "Priorities never change ratings; capped GDD unit tests; all other tests", t, "failed" not in t))
    v11 = pd.read_csv(PROCESSED / "v11_smap_power.csv", index_col=0) if (PROCESSED / "v11_smap_power.csv").exists() else None
    if v11 is not None:
        rows.append(("V11", "SMAP L4 vs POWER root-zone percentiles, 15 Jun–15 Aug (ρ ≥ 0.6 and ≥ 70% flag agreement)",
                     " · ".join(f"{fid[-1].upper()} ρ {r.spearman:.2f}, flags {r.flags_agree}" for fid, r in v11.iterrows()), bool(v11["pass"].all())))
    v12 = []
    for fid in FIELDS:
        tr = json.loads((PROCESSED / fid / "field_static.json").read_text())["terrain"]
        v12.append((fid, tr["mean_slope_pct"]["value"], tr["ref_3dep_10m_pct"]["value"]))
    rows.append(("V12", "Smoothed NASADEM mean slope within ±0.5 points of USGS 3DEP lidar",
                 " · ".join(f"{f[-1].upper()} {a:.2f}% vs {b:.2f}%" for f, a, b in v12), all(abs(a - b) <= 0.5 for _, a, b in v12)))
    v13 = _csv("v13_usdm_windows.csv")
    if v13 is not None:
        dry = v13[v13.power_dry]
        missed = v13[v13.dry_d1 & ~v13.power_dry]
        rows.append(("V13", "Dry calls vs U.S. Drought Monitor, Story County (reported, no pass bar)",
                     f"{int(dry.dry_d0.sum())}/{len(dry)} dry calls at D0 or worse, {int(dry.dry_d1.sum())} at D1 or worse; missed D1 windows: "
                     + ", ".join(f"{r.field[-1].upper()} {r.season}" for r in missed.itertuples()), None))
    mark = {True: "pass", False: "FAIL", None: "reported"}
    lines = ["# Validation results", "", "Generated by `python prep/validate_all.py` from the committed evidence (handoff §15).", "",
             "| ID | Test | Result | Status |", "|---|---|---|---|"]
    lines += [f"| {i} | {t} | {r} | {mark[p]} |" for i, t, r, p in rows]
    OUT.write_text("\n".join(lines) + "\n")
    for i, _t, r, p in rows:
        print(f"{i:8} {mark[p]:9} {r}")


if __name__ == "__main__":
    main()
