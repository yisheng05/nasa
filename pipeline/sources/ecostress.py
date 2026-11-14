"""ECOSTRESS Evaporative Stress Index (ECO_L4T_ESI v002, 70 m) over a field, from AppEEARS area outputs.

ESI is actual over potential evapotranspiration: lower means more water stress. Each
scene is reduced to the median over the field interior's clear pixels (ECOSTRESS cloud
layer == 0). Exact zeros are treated as missing: on the demo fields they are 0.5% of
values, concentrated in two scenes, with nothing between 0 and 0.05, so they behave
like failed retrievals rather than real readings.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask

from ..geo import reproject

NAME = re.compile(r"ECO_L4T_ESI\.002_(ESI|cloud)_doy(\d{7})(\d{6})_aid\d+_\w+\.tif$")
MIN_CLEAR_SHARE = 0.5  # a scene is usable when at least half the interior pixels are clear and valid


def field_scenes(folder: Path, interior_wgs84) -> pd.DataFrame:
    """One row per ECOSTRESS overpass: interior pixels, clear valid pixels, median ESI, usable flag."""
    files: dict[str, dict[str, Path]] = {}
    for p in Path(folder).rglob("*.tif"):
        m = NAME.search(p.name)
        if m:
            files.setdefault(m.group(2) + m.group(3), {})[m.group(1)] = p
    rows, masks = [], {}
    for key, fs in sorted(files.items()):
        if "ESI" not in fs:
            continue
        with rasterio.open(fs["ESI"]) as ds:
            a = ds.read(1).astype(float)
            ck = (ds.crs.to_string(), ds.transform, ds.shape)
            if ck not in masks:
                geom = reproject(interior_wgs84, 4326, ds.crs.to_epsg())
                masks[ck] = geometry_mask([geom], out_shape=ds.shape, transform=ds.transform, invert=True)
            inside = masks[ck]
        ok = inside & np.isfinite(a) & (a > 0)
        if "cloud" in fs:
            with rasterio.open(fs["cloud"]) as cs:
                ok &= cs.read(1) == 0
        n_in, n_ok = int(inside.sum()), int(ok.sum())
        rows.append({
            "time": pd.to_datetime(key, format="%Y%j%H%M%S"),
            "n_interior": n_in,
            "n_clear": n_ok,
            "esi": round(float(np.median(a[ok])), 4) if n_ok else np.nan,
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["date"] = df["time"].dt.normalize()
    df["usable"] = (df["n_clear"] >= MIN_CLEAR_SHARE * df["n_interior"]) & df["esi"].notna()
    return df
