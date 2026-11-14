"""NASA POWER daily point data (community AG). No login needed."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import requests

from ..config import POWER_START, RAW, SEASONS

API = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMS = ("T2M_MAX", "T2M_MIN", "PRECTOTCORR", "GWETROOT")


def fetch(lat: float, lon: float, start: int = POWER_START, end: date | None = None, params=PARAMS) -> pd.DataFrame:
    end = end or date(SEASONS.stop - 1, 12, 31)
    key = RAW / "power" / f"power_{lat:.3f}_{lon:.3f}_{start}_{end:%Y%m%d}_{'-'.join(params)}.json"
    key.parent.mkdir(parents=True, exist_ok=True)
    if not key.exists():
        r = requests.get(
            API,
            params={
                "parameters": ",".join(params),
                "community": "AG",
                "latitude": lat,
                "longitude": lon,
                "start": f"{start}0101",
                "end": f"{end:%Y%m%d}",
                "format": "JSON",
            },
            timeout=300,
        )
        r.raise_for_status()
        key.write_text(r.text)
    payload = json.loads(key.read_text())
    fill = payload.get("header", {}).get("fill_value", -999.0)
    df = pd.DataFrame(payload["properties"]["parameter"])
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df = df.mask(df == fill)
    df.attrs["power_cell"] = payload.get("geometry", {}).get("coordinates")
    df.attrs["sources"] = payload.get("header", {}).get("sources")
    return df
