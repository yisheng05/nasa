"""Demo-field selection and loading.

Selection finds blocks of pixels whose CDL class strictly alternates corn/soybean
in every season, then vectorises the largest blocks as candidate field polygons.
The chosen polygons are saved to pipeline/demo_fields.geojson and reviewed on NAIP.
"""

from __future__ import annotations

import json

import numpy as np
from scipy import ndimage
from shapely.geometry import shape

from .config import ALBERS, CORN, DEMO_FIELDS, SEASONS, SOY
from .geo import approx_pixels, area_ha, interior, reproject, to_wgs84
from .sources import cdl


def alternation_stack(center_lonlat: tuple[float, float], half_m: float = 5000.0, years=SEASONS):
    """CDL stack for a square window, plus a boolean mask of strict corn/soy alternation."""
    from shapely.geometry import Point

    c = reproject(Point(*center_lonlat), 4326, ALBERS)
    bounds = (c.x - half_m, c.y - half_m, c.x + half_m, c.y + half_m)
    layers, tr = [], None
    for y in years:
        a, tr = cdl.export_window(y, bounds)
        layers.append(a)
    stack = np.stack(layers)  # (years, rows, cols)
    is_cs = np.isin(stack, (CORN, SOY))
    alternates = np.all(is_cs, axis=0) & np.all(stack[1:] != stack[:-1], axis=0)
    return stack, alternates, tr


def _largest_rectangle(mask: np.ndarray) -> tuple[int, int, int, int]:
    """Largest axis-aligned all-True rectangle: (row0, col0, row1, col1), exclusive ends."""
    rows, cols = mask.shape
    heights = np.zeros(cols, dtype=int)
    best, best_rc = 0, (0, 0, 0, 0)
    for r in range(rows):
        heights = np.where(mask[r], heights + 1, 0)
        stack: list[int] = []
        for c in range(cols + 1):
            h = heights[c] if c < cols else 0
            while stack and heights[stack[-1]] >= h:
                top_h = heights[stack.pop()]
                left = stack[-1] + 1 if stack else 0
                area = top_h * (c - left)
                if area > best:
                    best, best_rc = area, (r - top_h + 1, left, r + 1, c)
            stack.append(c)
    return best_rc


def candidate_fields(stack, alternates, transform, min_ha: float = 25.0, top: int = 12) -> list[dict]:
    """Connected blocks of alternating pixels, largest first.

    Wet spots inside a block (prairie potholes, which CDL labels inconsistently)
    are filled as part of the field. Each block is reduced to its largest
    inscribed rectangle, which usually isolates a single management unit.
    """
    from shapely.geometry import box

    clean = ndimage.binary_opening(alternates, structure=np.ones((3, 3)))
    labels, n = ndimage.label(clean)
    if n == 0:
        return []
    sizes = ndimage.sum(clean, labels, index=np.arange(1, n + 1))
    order = np.argsort(sizes)[::-1]
    out = []
    for idx in order[:top]:
        lab = idx + 1
        mask = ndimage.binary_fill_holes(labels == lab)
        r0, c0, r1, c1 = _largest_rectangle(mask)
        x0, y0 = transform * (c0, r1)
        x1, y1 = transform * (c1, r0)
        poly = box(x0, y0, x1, y1)
        ha = poly.area / 1e4
        if ha < min_ha:
            continue
        first = int(np.bincount(stack[0][r0:r1, c0:c1].ravel()).argmax())
        geom = to_wgs84(poly)
        out.append(
            {
                "geometry": geom,
                "area_ha": round(ha, 1),
                "corn_years": "even" if (SEASONS.start % 2 == 0) == (first == CORN) else "odd",
                "centroid": (round(geom.centroid.x, 5), round(geom.centroid.y, 5)),
            }
        )
    return out


def save_demo_fields(fields: list[dict], path=DEMO_FIELDS) -> None:
    feats = []
    for f in fields:
        props = {k: v for k, v in f.items() if k != "geometry"}
        feats.append({"type": "Feature", "properties": props, "geometry": f["geometry"].__geo_interface__})
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, indent=1))


def load_demo_fields(path=DEMO_FIELDS) -> list[dict]:
    fc = json.loads(path.read_text())
    out = []
    for feat in fc["features"]:
        geom = shape(feat["geometry"])
        inner = interior(geom)
        out.append(
            {
                **feat["properties"],
                "geometry": geom,
                "interior": inner,
                "area_ha": round(area_ha(geom), 1),
                "interior_pixels_approx": approx_pixels(inner),
            }
        )
    return out
