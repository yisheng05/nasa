"""Per-date field statistics from AppEEARS HLS outputs (handoff §8.1 steps 1-3, tests V1-V2).

Each NDVI GeoTIFF (HLS VI product) is paired with the Fmask GeoTIFF from the
surface-reflectance product for the same sensor and acquisition, clipped to the
field interior (one-pixel inward buffer), and reduced to a per-date median over
valid pixels.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask

from ..config import MIN_VALID_PIXELS
from ..geo import reproject

NAME = re.compile(
    r"^HLS(?P<sensor>[LS]30)(?P<vi>_VI)?\.020_(?P<layer>[A-Za-z0-9]+)_doy(?P<doy>\d{7})(?P<time>\d{6})?_aid\d+_(?P<zone>\w+)\.tif$"
)
NDVI_SCALE = 1e-4
NDVI_FILL = -19999

# HLS v2 Fmask bits: 1 cloud, 2 adjacent to cloud/shadow, 3 cloud shadow, 4 snow/ice, 5 water; 6-7 aerosol level.
BAD_BITS = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5)
FMASK_FILL = 255


def fmask_valid(fmask: np.ndarray, mask_high_aerosol: bool = True) -> np.ndarray:
    ok = (fmask != FMASK_FILL) & ((fmask & BAD_BITS) == 0)
    if mask_high_aerosol:
        ok &= ((fmask >> 6) & 0b11) != 0b11
    return ok


def index_files(folder: Path) -> pd.DataFrame:
    rows = []
    for p in folder.rglob("*.tif"):
        m = NAME.match(p.name)
        if m:
            d = m.groupdict()
            rows.append({**d, "path": p, "key": d["doy"] + (d["time"] or "")})
    return pd.DataFrame(rows)


def field_series(folder: Path, interior_wgs84) -> pd.DataFrame:
    """One row per acquisition: valid-pixel counts and NDVI median/quartiles over the field interior."""
    idx = index_files(folder)
    if idx.empty:
        return pd.DataFrame()
    ndvi = idx[idx.layer == "NDVI"].set_index(["sensor", "key"])["path"]
    fmask = idx[idx.layer == "Fmask"].set_index(["sensor", "key"])["path"]
    out, mask_cache = [], {}
    for (sensor, key), p_ndvi in ndvi.items():
        p_fm = fmask.get((sensor, key))
        if p_fm is None:
            continue
        with rasterio.open(p_ndvi) as a, rasterio.open(p_fm) as b:
            v = a.read(1)
            fm = b.read(1)
            ck = (a.crs.to_string(), a.transform, a.shape)
            if ck not in mask_cache:
                geom = reproject(interior_wgs84, 4326, a.crs.to_epsg())
                mask_cache[ck] = geometry_mask([geom], out_shape=a.shape, transform=a.transform, invert=True)
            inside = mask_cache[ck]
        ok = inside & fmask_valid(fm) & (v != NDVI_FILL)
        vals = v[ok] * NDVI_SCALE
        vals = vals[(vals > -1) & (vals < 1)]
        date = pd.to_datetime(key[:7], format="%Y%j")
        row = {
            "date": date,
            "sensor": sensor,
            "n_interior": int(inside.sum()),
            "n_valid": int(vals.size),
        }
        if vals.size:
            q25, q50, q75 = np.percentile(vals, [25, 50, 75])
            row.update({"ndvi_median": round(float(q50), 4), "ndvi_p25": round(float(q25), 4), "ndvi_p75": round(float(q75), 4)})
        out.append(row)
    df = pd.DataFrame(out).sort_values(["date", "sensor"]).reset_index(drop=True)
    df["valid_frac"] = (df["n_valid"] / df["n_interior"]).round(3)
    df["passes_v1"] = df["n_valid"] >= MIN_VALID_PIXELS
    return df


def season_density(df: pd.DataFrame, months=(4, 10)) -> pd.DataFrame:
    """V2: valid (V1-passing) observation dates per season, April-October."""
    d = df[df.passes_v1 & df.date.dt.month.between(*months)]
    n = d.groupby(d.date.dt.year)["date"].nunique().rename("valid_dates_apr_oct")
    return n.to_frame()
