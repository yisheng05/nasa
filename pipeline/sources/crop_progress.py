"""USDA NASS weekly Crop Progress: Iowa % corn silked, for V4.

Release text files come from the USDA ESMIS archive (esmis.nal.usda.gov, "Crop
Progress"), cached under data/raw/crop_progress/. Each Monday release has a "Corn
Silking - Selected States" table; the Iowa row's third column is the week just ended.
QuickStats would be simpler but needs an API key in the URL.
"""

from __future__ import annotations

import re
from datetime import date

import numpy as np
import pandas as pd
import requests

from ..config import RAW

LIST_URL = "https://esmis.nal.usda.gov/publication/crop-progress"
BASE = "https://esmis.nal.usda.gov"
CACHE = RAW / "crop_progress"


def release_links(first_year: int) -> dict[str, str]:
    """Release date -> .txt link for every release back to 1 June of first_year (newest first, 10 per page)."""
    rel: dict[str, str] = {}
    s = requests.Session()
    for page in range(200):
        t = s.get(LIST_URL, params={"page": f"{page},0"}, timeout=60).text
        for m in re.finditer(r'<time datetime="(\d{4}-\d{2}-\d{2})T[^"]*">[^<]*</time>\s*</td>\s*<td[^>]*>(.*?)</td>', t, re.DOTALL):
            txt = re.findall(r'href="([^"]+\.txt)"', m.group(2))
            if txt:
                rel.setdefault(m.group(1), txt[0])
        if rel and min(rel) < f"{first_year}-06-01":
            break
    return rel


def fetch(years: range) -> pd.Series:
    """Iowa % corn silked by week ending, June-August of each year (cached)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    have = {p.stem for p in CACHE.glob("*.txt")}
    need = [f"{y}-{m:02d}" for y in years for m in (6, 7, 8)]
    if not all(any(h.startswith(n) for h in have) for n in need):
        s = requests.Session()
        for d, u in release_links(years.start).items():
            if d[:7] in need and d not in have:
                r = s.get(BASE + u, timeout=60)
                r.raise_for_status()
                (CACHE / f"{d}.txt").write_bytes(r.content)
    obs = {}
    for p in sorted(CACHE.glob("*.txt")):
        row = parse_iowa_silking(p.read_text(errors="replace"))
        if row and row[0].year in years:
            obs[row[0]] = row[1]
    return pd.Series(obs, name="iowa_corn_silked_pct").sort_index().rename_axis("week_ending")


def parse_iowa_silking(text: str) -> tuple[pd.Timestamp, float] | None:
    i = text.find("Corn Silking - Selected States")
    if i < 0:
        return None
    block = text[i:i + 3000].splitlines()
    hdr = next((ln for ln in block if "Week ending" not in ln and re.search(r"[A-Z][a-z]+ \d+,", ln)), None)
    if hdr is None:
        return None
    yrs = block[block.index(hdr) + 1]
    md, yr = re.findall(r"([A-Z][a-z]+ \d+),", hdr)[2], re.findall(r"(\d{4})", yrs)[2]
    row = next((ln for ln in block if ln.startswith("Iowa")), None)
    if row is None:
        return None
    v = row.split(":", 1)[1].split()[2]
    pct = 0.0 if v == "-" else float(v) if v.replace(".", "").isdigit() else np.nan
    return pd.Timestamp(f"{md} {yr}"), pct


def milestones(silked: pd.Series, levels=(25, 50, 75)) -> dict[int, dict[int, date | None]]:
    """Per year, the interpolated date Iowa reached each % silked (0% assumed on 1 June)."""
    out = {}
    for y, g in silked.dropna().groupby(silked.dropna().index.year):
        jan1 = pd.Timestamp(f"{y}-01-01")
        g = pd.concat([pd.Series({pd.Timestamp(f"{y}-06-01"): 0.0}), g]).sort_index()
        x, v = (g.index - jan1).days.values, np.maximum.accumulate(g.values)
        out[int(y)] = {q: (jan1 + pd.Timedelta(days=float(np.interp(q, v, x)))).date() if v.max() >= q else None for q in levels}
    return out
