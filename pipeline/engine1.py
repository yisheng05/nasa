"""Engine 1: Field History (handoff §8.1).

From per-date field NDVI (HLS, Fmask-screened, V1-passing) and the crop label per
season, reconstruct each season's timing and how much of the year the soil had
living cover.

Method (all thresholds provisional, for the team and an agronomist to agree):
- Smooth the whole multi-year record on a daily grid with a weighted Whittaker
  smoother (second differences), with one robust pass that down-weights
  observations far below the curve (residual cloud or shadow). The curve is then
  capped at the highest clear observation within +/-PEAK_CAP_DAYS (+ PEAK_CAP_TOL):
  a cloudy gap at the peak otherwise makes the smoother overshoot (2021 on Field A
  read 1.00 against a maximum observation of 0.91).
- Per season: peak = maximum of the smoothed curve between 1 Apr and 31 Oct.
  Green-up = first day on the rising limb at 50% of the spring amplitude (the same
  definition as MSLSP30NA's 50PCGI layer, for V3). Decline = last day on the falling
  limb at 50% of the autumn amplitude.
- Living cover = smoothed NDVI >= COVER_THRESHOLD *and* a clear observation at or
  above the threshold within SUPPORT_DAYS, so the smoother cannot invent cover across
  long winter gaps. It counts any green vegetation (crop, cover crop, weeds).
- End of living cover = first day after the peak when the curve drops below the
  threshold (canopy senescence, before harvest; harvest itself is not visible in NDVI).
  Each cover year runs from the previous season's end of living cover to this one's.
  Cover years differ in length, so the headline is the *share* of the cover year
  without living cover, expressed as months per year.
- Off-season living days = living-cover days in the cover year before (green-up - 30
  days): the window a cover crop would fill.
- Spring green: needs >= 2 clear observations in the core window 15 Mar-30 Apr (when
  cereal rye is visible, before termination); otherwise "insufficient data". Green =
  >= 2 observations >= SPRING_GREEN between 1 Mar and min(10 May, green-up - 30 days).
  Reported as "green detected, confirm with farmer", never as a cover crop: weeds and
  volunteers read the same (handoff §3.4).
- Autumn green after the end of living cover is recorded, not credited as cover crop.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import pairwise

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.linalg import spsolve

COVER_THRESHOLD = 0.40  # living-cover NDVI; senescent canopy reads ~0.28-0.39 on the demo fields
SPRING_GREEN = 0.40
WHITTAKER_LAMBDA = 1000.0
ROBUST_DROP = 0.10  # observations this far below the first fit get weight ROBUST_WEIGHT
ROBUST_WEIGHT = 0.3
MIN_SEASON_OBS = 8  # V2
MAX_GAP_HIGH_CONF = 30  # days, April-October
SUPPORT_DAYS = 30  # a living-cover day needs a clear observation >= threshold this close
PEAK_CAP_DAYS = 45
PEAK_CAP_TOL = 0.02


def whittaker(y: np.ndarray, w: np.ndarray, lam: float = WHITTAKER_LAMBDA) -> np.ndarray:
    n = len(y)
    d = sparse.diags([1.0, -2.0, 1.0], [0, 1, 2], shape=(n - 2, n))
    a = sparse.diags(w) + lam * (d.T @ d)
    return spsolve(a.tocsc(), w * y)


def smooth_daily(obs: pd.DataFrame, start: str, end: str, lam: float = WHITTAKER_LAMBDA) -> pd.Series:
    """Daily smoothed NDVI from V1-passing observations (median per date across sensors)."""
    o = obs[obs["passes_v1"]].groupby("date")["ndvi_median"].median()
    days = pd.date_range(start, end, freq="D")
    y = pd.Series(0.0, index=days)
    w = pd.Series(0.0, index=days)
    inside = o.index.intersection(days)
    y[inside] = o[inside].to_numpy()
    w[inside] = 1.0
    z = whittaker(y.to_numpy(), w.to_numpy(), lam)
    resid = y.to_numpy() - z
    w2 = w.to_numpy().copy()
    w2[(w2 > 0) & (resid < -ROBUST_DROP)] = ROBUST_WEIGHT
    z = whittaker(y.to_numpy(), w2, lam)
    local_max = o.reindex(days).rolling(2 * PEAK_CAP_DAYS + 1, center=True, min_periods=1).max()
    cap = (local_max + PEAK_CAP_TOL).fillna(1.0).to_numpy()
    z = np.minimum(z, cap)
    return pd.Series(np.clip(z, -0.2, 1.0), index=days, name="ndvi_smooth")


@dataclass
class Season:
    season: int
    crop: str | None
    n_obs_apr_oct: int
    max_gap_apr_oct: int | None
    peak_date: str | None = None
    peak_ndvi: float | None = None
    greenup_date: str | None = None
    decline_date: str | None = None
    integrated_ndvi: float | None = None
    living_cover_end: str | None = None
    cover_year_start: str | None = None
    cover_year_end: str | None = None
    cover_year_partial: bool = False
    cover_year_days: int | None = None
    living_cover_days: int | None = None
    no_living_cover_days: int | None = None
    no_living_cover_share: float | None = None
    off_season_living_days: int | None = None
    spring_green: str = "insufficient data"
    spring_green_obs: int = 0
    autumn_green_obs: int = 0
    confidence: str = "low"
    note: str = ""


def _first_cross_up(s: pd.Series, level: float) -> pd.Timestamp | None:
    hit = s[s >= level]
    return hit.index[0] if len(hit) else None


def _last_at_or_above(s: pd.Series, level: float) -> pd.Timestamp | None:
    hit = s[s >= level]
    return hit.index[-1] if len(hit) else None


def _max_gap(dates: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp) -> int | None:
    d = sorted(set(dates[(dates >= start) & (dates <= end)]))
    if not d:
        return None
    pts = [start, *d, end]
    return int(max((b - a).days for a, b in pairwise(pts)))


def living_mask(good: pd.DataFrame, z: pd.Series, threshold: float = COVER_THRESHOLD) -> pd.Series:
    """Daily living-cover flag: smoothed NDVI at/above threshold AND a clear observation at/above it within SUPPORT_DAYS."""
    green_obs = pd.Series(1.0, index=pd.DatetimeIndex(good.loc[good.ndvi_median >= threshold, "date"]).unique())
    support = green_obs.reindex(z.index).fillna(0).rolling(2 * SUPPORT_DAYS + 1, center=True, min_periods=1).max() > 0
    return (z >= threshold) & support


def run(obs: pd.DataFrame, crops: dict[int, str], seasons: list[int], threshold: float = COVER_THRESHOLD) -> tuple[list[Season], pd.Series]:
    """Engine 1 for one field. Returns per-season records and the daily smoothed series."""
    seasons = sorted(seasons)
    start, end = f"{seasons[0]}-01-01", f"{seasons[-1]}-12-31"
    z = smooth_daily(obs, start, end)
    good = obs[obs["passes_v1"]]
    gdates = pd.DatetimeIndex(good["date"])
    living = living_mask(good, z, threshold)
    out: list[Season] = []
    prev_harvest: pd.Timestamp | None = None
    for y in seasons:
        a0, a1 = pd.Timestamp(f"{y}-04-01"), pd.Timestamp(f"{y}-10-31")
        n_obs = int(((gdates >= a0) & (gdates <= a1)).sum())
        s = Season(season=y, crop=crops.get(y), n_obs_apr_oct=n_obs, max_gap_apr_oct=_max_gap(gdates, a0, a1))
        if n_obs < 3:
            s.note = "too few clear observations in April-October"
            out.append(s)
            prev_harvest = None
            continue
        grow = z[a0:a1]
        peak_day = grow.idxmax()
        peak = float(grow.max())
        spring = z[pd.Timestamp(f"{y}-03-01") : peak_day]
        base_up = float(spring.min())
        autumn = z[peak_day : pd.Timestamp(f"{y}-12-31")]
        base_down = float(autumn.min())
        up_level = base_up + 0.5 * (peak - base_up)
        down_level = base_down + 0.5 * (peak - base_down)
        greenup = _first_cross_up(z[spring.idxmin() : peak_day], up_level)
        decline = _last_at_or_above(z[peak_day : autumn.idxmin()], down_level)
        below = autumn[autumn < threshold]
        harvest = below.index[0] if len(below) else None
        s.peak_date, s.peak_ndvi = peak_day.date().isoformat(), round(peak, 3)
        s.greenup_date = greenup.date().isoformat() if greenup is not None else None
        s.decline_date = decline.date().isoformat() if decline is not None else None
        if greenup is not None and decline is not None:
            s.integrated_ndvi = round(float((z[greenup:decline] - base_up).clip(lower=0).sum()), 1)
        s.living_cover_end = harvest.date().isoformat() if harvest is not None else None
        # cover year: previous end of living cover (exclusive) to this one (inclusive)
        cy0 = prev_harvest + pd.Timedelta(days=1) if prev_harvest is not None else pd.Timestamp(f"{y}-01-01")
        s.cover_year_partial = prev_harvest is None
        if harvest is not None:
            win = living[cy0:harvest]
            s.cover_year_start, s.cover_year_end = cy0.date().isoformat(), harvest.date().isoformat()
            s.cover_year_days = len(win)
            s.living_cover_days = int(win.sum())
            s.no_living_cover_days = int(len(win) - s.living_cover_days)
            s.no_living_cover_share = round(s.no_living_cover_days / len(win), 3)
            if greenup is not None:
                s.off_season_living_days = int(living[cy0 : greenup - pd.Timedelta(days=30)].sum())
        # spring green before the cash crop
        if greenup is not None:
            core = good[(good.date >= pd.Timestamp(f"{y}-03-15")) & (good.date <= pd.Timestamp(f"{y}-04-30"))]
            w0, w1 = pd.Timestamp(f"{y}-03-01"), min(pd.Timestamp(f"{y}-05-10"), greenup - pd.Timedelta(days=30))
            sw = good[(good.date >= w0) & (good.date <= w1)]
            s.spring_green_obs = int((sw.ndvi_median >= SPRING_GREEN).sum())
            if len(core) < 2:
                s.spring_green = "insufficient data"
            elif s.spring_green_obs >= 2:
                s.spring_green = "green detected (confirm with farmer)"
            elif s.spring_green_obs == 1:
                s.spring_green = "possible (one clear observation)"
            else:
                s.spring_green = "none detected"
        if harvest is not None:
            aw = good[(good.date >= harvest + pd.Timedelta(days=7)) & (good.date <= pd.Timestamp(f"{y}-12-15"))]
            s.autumn_green_obs = int((aw.ndvi_median >= SPRING_GREEN).sum())
        gap = s.max_gap_apr_oct or 999
        s.confidence = "high" if n_obs >= MIN_SEASON_OBS and gap <= MAX_GAP_HIGH_CONF else "moderate" if n_obs >= MIN_SEASON_OBS else "low"
        out.append(s)
        prev_harvest = harvest
    return out, z


def summarise(seasons: list[Season]) -> dict:
    full = [s for s in seasons if s.no_living_cover_share is not None and not s.cover_year_partial]
    share = [s.no_living_cover_share for s in full]
    off = [s.off_season_living_days for s in full if s.off_season_living_days is not None]
    return {
        "complete_cover_years": len(full),
        "mean_no_living_cover_share": round(float(np.mean(share)), 3) if share else None,
        "no_living_cover_months_per_year": round(float(np.mean(share)) * 12, 1) if share else None,
        "mean_off_season_living_days": round(float(np.mean(off)), 0) if off else None,
        "spring_green_seasons": sum(s.spring_green.startswith("green detected") for s in seasons),
        "spring_assessable_seasons": sum(s.spring_green != "insufficient data" for s in seasons),
        "autumn_green_seasons": sum(s.autumn_green_obs >= 2 for s in seasons),
    }


def to_records(seasons: list[Season]) -> list[dict]:
    return [asdict(s) for s in seasons]
