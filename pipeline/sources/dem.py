"""Field slope from NASADEM (NASA's reprocessed SRTM, 1 arc-second) via Microsoft Planetary Computer.

The Field Shift Resources list SRTM; NASADEM is NASA's improved SRTM product and
is readable without a login, so it stands in for SRTMGL1 (AppEEARS) here.

Raw 30 m SRTM/NASADEM slope is inflated by elevation noise on flat ground. On the
demo fields (14 Nov) it read 3.8-4.2% against 1.5-2.0% from USGS 3DEP 10 m lidar.
A Gaussian filter (sigma 1.5 px) before the gradient brings NASADEM within
0.2 percentage points of 3DEP and restores the field ranking (test V12).
"""

from __future__ import annotations

import numpy as np
import planetary_computer
import pystac_client
import rasterio
from rasterio.features import geometry_mask
from rasterio.vrt import WarpedVRT
from rasterio.warp import Resampling
from scipy import ndimage

from ..config import ALBERS
from ..geo import to_albers

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


SMOOTH_SIGMA_PX = 1.5


def _slope_pct(z: np.ndarray, res: float, sigma: float = 0.0) -> np.ndarray:
    if sigma:
        z = ndimage.gaussian_filter(z, sigma)
    dzdy, dzdx = np.gradient(z, res)
    return np.hypot(dzdx, dzdy) * 100


def field_slope(geom_wgs84, interior_wgs84, res: float = 30.0, sigma: float = SMOOTH_SIGMA_PX) -> dict:
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    minx, miny, maxx, maxy = geom_wgs84.buffer(0.003).bounds
    items = list(cat.search(collections=["nasadem"], bbox=[minx, miny, maxx, maxy]).items())
    if not items:
        raise RuntimeError("No NASADEM item for field")
    g = to_albers(geom_wgs84.buffer(0.003))
    xmin, ymin, xmax, ymax = g.bounds
    w, h = int((xmax - xmin) // res), int((ymax - ymin) // res)
    from affine import Affine

    tr = Affine(res, 0, xmin, 0, -res, ymax)
    with rasterio.open(items[0].assets["elevation"].href) as src, WarpedVRT(
        src, crs=f"EPSG:{ALBERS}", transform=tr, width=w, height=h, resampling=Resampling.bilinear
    ) as vrt:
        z = vrt.read(1).astype(float)
    inside = geometry_mask([to_albers(interior_wgs84)], out_shape=z.shape, transform=tr, invert=True)
    s = _slope_pct(z, res, sigma)[inside]
    raw = _slope_pct(z, res)[inside]
    return {
        "mean_slope_pct": round(float(np.mean(s)), 2),
        "p90_slope_pct": round(float(np.percentile(s, 90)), 2),
        "mean_slope_pct_unsmoothed": round(float(np.mean(raw)), 2),
        "smoothing_sigma_px": sigma,
        "relief_m": round(float(np.ptp(z[inside])), 1),
        "pixels": int(s.size),
        "item": items[0].id,
    }


def reference_slope_3dep(geom_wgs84, interior_wgs84, res: float = 10.0) -> float:
    """Mean slope from USGS 3DEP 10 m lidar-derived DEM, used only as a validation reference (V12)."""
    cat = pystac_client.Client.open(STAC, modifier=planetary_computer.sign_inplace)
    bb = geom_wgs84.buffer(0.003).bounds
    items = list(cat.search(collections=["3dep-seamless"], bbox=bb, query={"gsd": {"eq": 10}}).items())
    if not items:
        raise RuntimeError("No 3DEP 10 m item for field")
    from affine import Affine

    g = to_albers(geom_wgs84.buffer(0.003))
    xmin, ymin, xmax, ymax = g.bounds
    w, h = int((xmax - xmin) // res), int((ymax - ymin) // res)
    tr = Affine(res, 0, xmin, 0, -res, ymax)
    with rasterio.open(items[0].assets["data"].href) as src, WarpedVRT(
        src, crs=f"EPSG:{ALBERS}", transform=tr, width=w, height=h, resampling=Resampling.bilinear
    ) as vrt:
        z = vrt.read(1).astype(float)
    inside = geometry_mask([to_albers(interior_wgs84)], out_shape=z.shape, transform=tr, invert=True)
    return round(float(_slope_pct(z, res)[inside].mean()), 2)
