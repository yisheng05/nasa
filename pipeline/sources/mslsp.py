"""NASA MSLSP30NA v011 (MuSLI Land Surface Phenology, 30 m, from HLS), for V3.

One netCDF per HLS tile per year, downloaded from LP DAAC with Earthdata login. Dates
are day of year relative to the product year (they can fall below 1 or above 365).
Up to two vegetation cycles per pixel per year; the cash crop's cycle is taken as the
one whose peak falls between 1 June and 30 September, so an early spring cycle (a cover
crop or weeds) is not mistaken for the crop's green-up. MSLSP uses EVI2 and its own
curve fit, so it is a semi-independent check of Engine 1's NDVI-based green-up.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import geometry_mask

from ..geo import reproject

FILL = 32767
PEAK_WINDOW = (152, 274)  # DOY: 1 Jun - 30 Sep (non-leap)
URL = "https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/MSLSP30NA.011/MSLSP_{tile}_{year}/MSLSP_{tile}_{year}.nc"


def download(tile: str, year: int, folder: Path) -> Path:
    """One tile-year (~165 MB) from LP DAAC; Earthdata login from ~/.netrc (requests applies it on the redirect)."""
    import requests

    p = Path(folder) / f"MSLSP_{tile}_{year}.nc"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        with requests.Session() as s, s.get(URL.format(tile=tile, year=year), stream=True, timeout=600) as r:
            r.raise_for_status()
            tmp = p.with_suffix(".part")
            with open(tmp, "wb") as fh:
                fh.writelines(r.iter_content(1 << 20))
            tmp.rename(p)
    return p


def _layer(path: Path, name: str):
    with rasterio.open(f"NETCDF:{path}:{name}") as d:
        return d.read(1), d.transform, d.crs


def field_greenup(path: Path, year: int, interior_wgs84) -> dict:
    """Median 50% green-up (50PCGI) of the summer cycle over the field interior."""
    gi1, transform, crs = _layer(path, "50PCGI")
    gi2, _, _ = _layer(path, "50PCGI_2")
    pk1, _, _ = _layer(path, "Peak")
    pk2, _, _ = _layer(path, "Peak_2")
    qa1, _, _ = _layer(path, "gupQA")
    qa2, _, _ = _layer(path, "gupQA_2")
    geom = reproject(interior_wgs84, 4326, crs.to_epsg())
    inside = geometry_mask([geom], out_shape=gi1.shape, transform=transform, invert=True)
    in1 = (pk1 >= PEAK_WINDOW[0]) & (pk1 <= PEAK_WINDOW[1]) & (gi1 != FILL)
    in2 = (pk2 >= PEAK_WINDOW[0]) & (pk2 <= PEAK_WINDOW[1]) & (gi2 != FILL)
    gi = np.where(in1, gi1, np.where(in2, gi2, FILL))
    qa = np.where(in1, qa1, np.where(in2, qa2, FILL))
    ok = inside & (gi != FILL)
    n_in, n_ok = int(inside.sum()), int(ok.sum())
    if not n_ok:
        return {"year": year, "n_interior": n_in, "n_valid": 0, "greenup_doy": None, "greenup_date": None}
    doy = float(np.median(gi[ok]))
    good = ok & (qa <= 2)
    return {
        "year": year,
        "n_interior": n_in,
        "n_valid": n_ok,
        "greenup_doy": doy,
        "greenup_date": (date(year, 1, 1) + timedelta(days=round(doy) - 1)).isoformat(),
        "iqr_days": float(np.subtract(*np.percentile(gi[ok], [75, 25]))),
        "share_qa_good": round(float(good.sum()) / n_ok, 2),
    }
