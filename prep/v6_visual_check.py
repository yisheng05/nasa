"""V6: visual check of Engine 1's off-season cover calls (handoff §15).

Samples 10 off-season dates per field at random (fixed seed) from dates with a clear
HLS observation, fetches the same HLS v2.0 granule's true-colour bands (B04, B03, B02)
from NASA LP DAAC (Earthdata login via ~/.netrc; windowed reads of the COGs), and writes one numbered contact sheet per field with
the field interior outlined. The green / not-green call is NOT printed on the sheet:
it goes to a separate key file, so whoever rates the sheet does it blind.

Usage:  python prep/v6_visual_check.py OUT_DIR [--balanced]

--balanced: a supplementary set that tests the green class, which a purely random
off-season sample rarely contains: per field, 5 dates called green and 5 called not
green, all in true off-season months (September to May), shuffled before numbering.
Then fill data/processed/v6_visual_calls.csv (rater's call per field and chip number)
and compare with the key.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
import requests
from PIL import Image, ImageDraw
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import engine1 as E1
from pipeline import fields
from pipeline.config import PROCESSED
from pipeline.geo import reproject

CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
SHORT_NAME = {"L30": "HLSL30", "S30": "HLSS30"}
UTM15N = 32615  # HLS tile T15TVG
SEED, N_PER_FIELD, BUFFER_M, SCALE = 2026, 10, 240, 8


def off_season_dates(fid: str) -> pd.DataFrame:
    """Clear observations outside every season's green-up .. end-of-living-cover span, with Engine 1's call."""
    e1 = json.loads((PROCESSED / fid / "engine1.json").read_text())
    obs = pd.read_parquet(PROCESSED / fid / "hls_obs.parquet")
    z = pd.read_parquet(PROCESSED / fid / "ndvi_smooth.parquet")["ndvi_smooth"]
    good = obs[obs["passes_v1"]].copy()
    living = E1.living_mask(good, z, e1["method"]["cover_threshold_ndvi"])
    spans = [(pd.Timestamp(s["greenup_date"]), pd.Timestamp(s["living_cover_end"]))
             for s in e1["seasons"] if s.get("greenup_date") and s.get("living_cover_end")]
    good["date"] = pd.to_datetime(good["date"])
    in_season = good["date"].apply(lambda d: any(a <= d <= b for a, b in spans))
    off = good[~in_season].drop_duplicates("date").copy()
    off["call"] = off["date"].map(lambda d: "green" if bool(living.get(d.normalize(), False)) else "not green")
    return off


def _granule_links(sensor: str, day: pd.Timestamp, lon: float, lat: float) -> dict[str, str] | None:
    r = requests.get(CMR, params={"short_name": SHORT_NAME[sensor], "version": "2.0", "point": f"{lon},{lat}",
                                  "temporal": f"{day:%Y-%m-%d}T00:00:00Z,{day:%Y-%m-%d}T23:59:59Z", "page_size": 10}, timeout=60)
    r.raise_for_status()
    for e in r.json()["feed"]["entry"]:
        if "T15TVG" in e["title"]:
            hrefs = [lk["href"] for lk in e["links"] if lk["href"].startswith("https") and lk["href"].endswith(".tif")]
            return {b: next(h for h in hrefs if h.endswith(f".{b}.tif")) for b in ("B04", "B03", "B02")}
    return None


def chip(sensor: str, day: pd.Timestamp, geom_wgs84, interior_wgs84) -> np.ndarray | None:
    c = geom_wgs84.centroid
    links = _granule_links(sensor, day, c.x, c.y)
    if not links:
        return None
    bands = []
    for b in ("B04", "B03", "B02"):
        with rasterio.open(links[b]) as ds:
            g = reproject(geom_wgs84, 4326, UTM15N)
            x0, y0, x1, y1 = g.bounds
            win = from_bounds(x0 - BUFFER_M, y0 - BUFFER_M, x1 + BUFFER_M, y1 + BUFFER_M, ds.transform)
            a = ds.read(1, window=win, boundless=True, fill_value=-9999).astype(float)
            tr = ds.window_transform(win)
        bands.append(a)
    rgb = np.dstack(bands)
    rgb = np.where(rgb < 0, np.nan, rgb * 1e-4)
    img = np.clip(np.nan_to_num(rgb, nan=0) / 0.20, 0, 1) ** (1 / 1.6)
    inner = reproject(interior_wgs84, 4326, UTM15N)
    edge = geometry_mask([inner.boundary.buffer(12)], out_shape=img.shape[:2], transform=tr, invert=True)
    img[edge] = [1.0, 0.1, 0.9]  # magenta outline: field interior
    return (img * 255).astype(np.uint8)


def main(out: Path, balanced: bool = False) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cookies = str(out / "urs_cookies")
    os.environ.update({"GDAL_HTTP_COOKIEFILE": cookies, "GDAL_HTTP_COOKIEJAR": cookies, "GDAL_HTTP_NETRC": "YES",
                       "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MAX_RETRY": "3"})
    rng = np.random.default_rng(SEED)
    key = []
    for f in fields.load_demo_fields():
        fid = f["id"]
        off = off_season_dates(fid)
        if balanced:
            rng = np.random.default_rng(SEED + 1)
            core = off[~off["date"].dt.month.isin([6, 7, 8])]
            parts = [core[core.call == c] for c in ("green", "not green")]
            pick = pd.concat([g.iloc[rng.choice(len(g), size=min(5, len(g)), replace=False)] for g in parts])
            pick = pick.iloc[rng.permutation(len(pick))]
        else:
            pick = off.iloc[np.sort(rng.choice(len(off), size=min(N_PER_FIELD, len(off)), replace=False))]
        tiles = []
        for n, (_, r) in enumerate(pick.iterrows(), start=1):
            im = chip(r["sensor"], r["date"], f["geometry"], f["interior"])
            key.append({"field": fid, "chip": n, "date": r["date"].date().isoformat(), "sensor": r["sensor"],
                        "ndvi_median": r["ndvi_median"], "engine1_call": r["call"], "image": im is not None})
            if im is not None:
                tiles.append((n, Image.fromarray(im).resize((im.shape[1] * SCALE, im.shape[0] * SCALE), Image.NEAREST)))
        w = max(t.width for _, t in tiles); h = max(t.height for _, t in tiles)
        sheet = Image.new("RGB", (5 * (w + 10) + 10, 2 * (h + 40) + 10), "white")
        d = ImageDraw.Draw(sheet)
        for k, (n, t) in enumerate(tiles):
            x, y = 10 + (k % 5) * (w + 10), 10 + (k // 5) * (h + 40)
            sheet.paste(t, (x, y + 30))
            d.text((x, y + 8), f"#{n}", fill="black")
        sheet.save(out / f"v6_{'balanced_' if balanced else ''}{fid}.png")
        print(fid, "off-season clear dates:", len(off), "of which called green:", int((off.call == "green").sum()), "| sampled:", len(pick))
    (out / f"v6_{'balanced_' if balanced else ''}key.json").write_text(json.dumps(key, indent=1, default=str))


if __name__ == "__main__":
    main(Path(sys.argv[1]), balanced="--balanced" in sys.argv)
