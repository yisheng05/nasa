"""U.S. Drought Monitor county statistics, weekly: a neutral reference for Engine 2's dry calls.

The Drought Monitor (NDMC at UNL, USDA, NOAA) is a weekly expert synthesis of many
indicators, including precipitation, soil-moisture models and NASA satellite products, drawn
by county. Its categories are percentile-based: D0 abnormally dry (21st–30th percentile),
D1 moderate drought (11th–20th), D2 severe (6th–10th), D3 (3rd–5th), D4 (0–2nd). Engine 2's
"root-zone wetness below the 20th percentile" therefore lines up with D1 or worse.

Area shares here are cumulative (statisticsType=1): the D1 share includes D2–D4. It is
neither ground truth nor fully independent of SMAP, and a county is far coarser than a
field. Read agreement as corroboration, not accuracy.
"""

from __future__ import annotations

import json

import pandas as pd
import requests

from ..config import RAW, SEASONS

API = "https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"
DRY_AREA_PCT = 50  # a window is "dry" when on average at least half the county is in the category


def fetch(fips: str, start: int = SEASONS.start, end: int = SEASONS.stop - 1) -> pd.DataFrame:
    """Weekly maps for one county: valid_start, valid_end and cumulative area % for D0-D4."""
    key = RAW / "usdm" / f"county_{fips}_{start}_{end}_cumulative.json"
    key.parent.mkdir(parents=True, exist_ok=True)
    if not key.exists():
        r = requests.get(
            API,
            params={"aoi": fips, "startdate": f"1/1/{start}", "enddate": f"12/31/{end}", "statisticsType": 1},
            headers={"Accept": "application/json"},
            timeout=120,
        )
        r.raise_for_status()
        key.write_text(r.text)
    df = pd.DataFrame(json.loads(key.read_text()))
    df = df.rename(columns={"validStart": "valid_start", "validEnd": "valid_end"})
    df["valid_start"] = pd.to_datetime(df["valid_start"])
    df["valid_end"] = pd.to_datetime(df["valid_end"])
    return df[["valid_start", "valid_end", "none", "d0", "d1", "d2", "d3", "d4"]].sort_values("valid_start").reset_index(drop=True)


def window_stats(usdm: pd.DataFrame, start, end) -> dict:
    """Mean cumulative area % over the weekly maps whose valid week overlaps [start, end]."""
    w0, w1 = pd.Timestamp(start), pd.Timestamp(end)
    m = usdm[(usdm["valid_start"] <= w1) & (usdm["valid_end"] >= w0)]
    if m.empty:
        return {"maps": 0, "d0_pct": None, "d1_pct": None, "d2_pct": None, "dry_d1": None, "dry_d0": None}
    d0, d1, d2 = (round(float(m[c].mean()), 1) for c in ("d0", "d1", "d2"))
    return {"maps": len(m), "d0_pct": d0, "d1_pct": d1, "d2_pct": d2, "dry_d1": d1 >= DRY_AREA_PCT, "dry_d0": d0 >= DRY_AREA_PCT}
