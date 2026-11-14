"""USDA NASS Cropland Data Layer from the USDA CroplandCROS image service.

CropScape (nassgeodata.gmu.edu) failed TLS from the dev container, so this reads
the same CDL rasters from USDA SCINet's CroplandCROS ArcGIS ImageServer, which
holds 2008-2025 (2024-2025 published at 10 m; exported here at 30 m, nearest).
"""

from __future__ import annotations

import json
from functools import lru_cache

import numpy as np
import rasterio
import requests
from rasterio.features import geometry_mask

from ..config import ALBERS, CDL_CLASSES, RAW
from ..geo import to_albers

SERVICE = "https://pdi.scinet.usda.gov/image/rest/services/CDL_WM/ImageServer"
TIMEOUT = 90


@lru_cache(maxsize=1)
def year_to_raster_id() -> dict[int, int]:
    r = requests.get(
        f"{SERVICE}/query",
        params={"where": "1=1", "outFields": "OBJECTID,Year", "returnGeometry": "false", "f": "json"},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return {f["attributes"]["Year"]: f["attributes"]["OBJECTID"] for f in r.json()["features"]}


def export_window(year: int, bounds_albers: tuple[float, float, float, float], res: float = 30.0):
    """Return (array, transform) of CDL classes for an Albers bbox. Cached on disk."""
    xmin, ymin, xmax, ymax = bounds_albers
    w, h = round((xmax - xmin) / res), round((ymax - ymin) / res)
    key = f"cdl_{year}_{int(xmin)}_{int(ymin)}_{w}x{h}.tif"
    path = RAW / "cdl" / key
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        params = {
            "bbox": f"{xmin},{ymin},{xmax},{ymax}",
            "bboxSR": ALBERS,
            "imageSR": ALBERS,
            "size": f"{w},{h}",
            "format": "tiff",
            "pixelType": "U8",
            "interpolation": "RSP_NearestNeighbor",
            "mosaicRule": json.dumps(
                {"mosaicMethod": "esriMosaicLockRaster", "lockRasterIds": [year_to_raster_id()[year]]}
            ),
            "f": "image",
        }
        r = requests.get(f"{SERVICE}/exportImage", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        if "tiff" not in r.headers.get("content-type", ""):
            raise RuntimeError(f"CDL {year}: unexpected response {r.text[:200]}")
        path.write_bytes(r.content)
    with rasterio.open(path) as ds:
        return ds.read(1), ds.transform


def field_stats(geom_wgs84, year: int) -> dict:
    """Majority CDL class over a field and its share of the field's pixels."""
    g = to_albers(geom_wgs84)
    xmin, ymin, xmax, ymax = g.bounds
    pad = 60
    arr, tr = export_window(year, (xmin - pad, ymin - pad, xmax + pad, ymax + pad))
    inside = geometry_mask([g], out_shape=arr.shape, transform=tr, invert=True)
    vals = arr[inside]
    vals = vals[vals > 0]
    if vals.size == 0:
        return {"year": year, "class": None, "name": None, "share": 0.0, "pixels": 0}
    codes, counts = np.unique(vals, return_counts=True)
    i = int(np.argmax(counts))
    code = int(codes[i])
    return {
        "year": year,
        "class": code,
        "name": CDL_CLASSES.get(code, f"class {code}"),
        "share": round(float(counts[i] / vals.size), 3),
        "pixels": int(vals.size),
    }


