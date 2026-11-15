"""Engine 2: Stress Recurrence (handoff §8.2).

For each past season: estimate the crop's sensitive window, test whether regional
water or heat stress fell inside it, compare the season's vigour with this field's
own median for the same crop, and summarise how often stress recurs.

Provisional choices, for the team and an agronomist to agree:
- Corn silking = the day capped GDD (°C, handoff §7.4) accumulated from Engine 1's
  green-up reaches SILK_GDD_FROM_GREENUP. Purdue NCH-40 puts silking at ~1,400 °F GDD
  from planting; if the 50% green-up point sits near V8-V10 (~610-740 °F), ~660-790 °F
  (~370-440 °C) remain, so 400 °C is used. Cross-checked against the NDVI peak, which
  in corn usually falls at or shortly after silking. V4 (Iowa Crop Progress) will
  calibrate this.
- Corn window: 14 days centred on silking. Soybean window (pod set to seed fill,
  ~R3-R6): NDVI peak - 14 days to peak + 21 days, because soybean development follows
  day length and GDD predicts it poorly (§7.4).
- Percentiles: each day against the same calendar day +/- 7 days in 1991-2020 (POWER),
  mid-rank for ties (GWETROOT is reported to 0.01).
- Stress-window season: root-zone wetness below the 20th percentile on >= 50% of window
  days (7 of 14 for corn), or Tmax above the 80th percentile on >= 5/14 of window days.
- Relative vigour: peak NDVI vs this field's median for the same crop (+/- 0.03), and
  integrated NDVI (green-up to decline) vs its median (+/- 10%). "below" if either is
  below; "above" if both are above; else "similar"; "uncertain" where Engine 1 flagged
  the peak. Peak NDVI saturates near 0.9 in dense canopies, so "similar" under stress
  (Scenario B) may partly reflect saturation rather than true buffering.
- Base rate: each season's window is also tested in every 1991-2020 year (same calendar
  dates). The share flagged is the chance of a flag in a typical year; summed over seasons
  it gives the *expected* number of stress seasons, so "k of n" is read against chance.
  (With these rules a flag is not rare: the heat rule alone fires in roughly 1 year in 8
  under independent days, more with persistent weather.)
- Confidence is capped at "moderate": the drivers are regional (POWER ~0.5°, SMAP 9 km).
- Field-scale check (step 6): usable ECOSTRESS ESI scenes (70 m) from 10 days before to
  10 days after the window. With at least ESI_MIN_SCENES, the season's median ESI is
  "low" when it sits ESI_LOW_DROP or more below this field's own median for all usable
  scenes 15 Jun-31 Aug. A low ESI that agrees with a regional flag raises confidence to
  "moderate-high"; disagreement keeps it at "moderate" and is reported. A low ESI with no
  regional flag is reported as field-level stress the regional data missed.
- U.S. Drought Monitor (V13, display only): the county's majority category over the weekly
  maps overlapping each window, beside the POWER dry call. It never changes a flag, a
  scenario or a confidence level: it was used to validate the rules, so it is not used
  to tune them.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from .config import CLIMATE_BASELINE
from .gdd import gdd_day
from .sources.usdm import window_stats as usdm_window

SILK_GDD_FROM_GREENUP = 400.0
CORN_WINDOW_DAYS = 14
SOY_WINDOW = (-14, 21)  # days relative to NDVI peak
DRY_PCT, HOT_PCT = 20.0, 80.0
DRY_SHARE, HOT_SHARE = 7 / 14, 5 / 14
VIGOUR_BAND = 0.03
INTEGRATED_BAND = 0.10  # relative
POOL_HALF_DAYS = 7
CONF_ORDER = ["low", "moderate", "high"]
ESI_PAD_DAYS = 10
ESI_MIN_SCENES = 2
ESI_LOW_DROP = 0.05


def _noleap_doy(idx: pd.DatetimeIndex) -> np.ndarray:
    """Day of year on a 365-day calendar; 29 Feb maps to 28 Feb."""
    ref = pd.to_datetime({"year": 2001, "month": idx.month, "day": np.where((idx.month == 2) & (idx.day == 29), 28, idx.day)})
    return ref.dt.dayofyear.to_numpy()


def doy_percentile(s: pd.Series, baseline: tuple[int, int] = CLIMATE_BASELINE, half: int = POOL_HALF_DAYS) -> pd.Series:
    """Percentile (0-100) of each value against the same calendar day +/- half days in the baseline years."""
    s = s.dropna()
    doy = _noleap_doy(s.index)
    in_base = (s.index.year >= baseline[0]) & (s.index.year <= baseline[1])
    bvals, bdoy = s.to_numpy()[in_base], doy[in_base]
    pools = {}
    for k in range(1, 366):
        dist = np.minimum(np.abs(bdoy - k), 365 - np.abs(bdoy - k))
        pools[k] = np.sort(bvals[dist <= half])
    out = np.empty(len(s))
    vals = s.to_numpy()
    for i, (v, k) in enumerate(zip(vals, doy, strict=True)):
        p = pools[k]
        lo, hi = np.searchsorted(p, v, side="left"), np.searchsorted(p, v, side="right")
        out[i] = (lo + hi) / 2 / len(p) * 100
    return pd.Series(out, index=s.index, name=f"{s.name}_pct")


@dataclass
class StressSeason:
    season: int
    crop: str | None
    window_start: str | None = None
    window_end: str | None = None
    window_basis: str = ""
    silking_est: str | None = None
    peak_minus_silking_days: int | None = None
    dry_days: int | None = None
    hot_days: int | None = None
    window_days: int | None = None
    rain_mm: float | None = None
    gwetroot_mean_pct: float | None = None
    tmax_mean_pct: float | None = None
    stress_flag: bool = False
    drivers: list[str] = field(default_factory=list)
    base_rate: float | None = None  # share of 1991-2020 years flagged for the same calendar window
    smap_dry_days: int | None = None
    smap_agrees: bool | None = None
    esi_scenes: int | None = None
    esi_median: float | None = None
    esi_field_median: float | None = None
    esi_status: str | None = None  # "low", "not low", "insufficient"; None if no ECOSTRESS for the year
    esi_agrees: bool | None = None
    usdm_category: str | None = None  # Drought Monitor majority category over the window: "None", "D0".."D4"
    usdm_d0_pct: float | None = None  # mean share of the county in D0 or worse (cumulative)
    usdm_d1_pct: float | None = None
    usdm_d2_pct: float | None = None
    usdm_agrees: bool | None = None  # POWER dry call == Drought Monitor D1-or-worse majority
    peak_ndvi: float | None = None
    crop_median_peak: float | None = None
    integrated_rel: float | None = None  # (integrated NDVI - crop median) / crop median
    crop_n: int | None = None
    vigour: str = "uncertain"
    scenario: str = ""
    confidence: str = "low"
    note: str = ""


def _window(e1: dict, power: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp, str, pd.Timestamp | None, int | None] | None:
    crop = e1.get("crop")
    if crop == "corn" and e1.get("greenup_date"):
        g = pd.Timestamp(e1["greenup_date"])
        p = power.loc[g : pd.Timestamp(f"{g.year}-10-31")]
        cum = pd.Series(gdd_day(p["T2M_MAX"], p["T2M_MIN"]), index=p.index).cumsum()
        hit = cum[cum >= SILK_GDD_FROM_GREENUP]
        if not len(hit):
            return None
        silk = hit.index[0]
        half = CORN_WINDOW_DAYS // 2
        offset = (pd.Timestamp(e1["peak_date"]) - silk).days if e1.get("peak_date") else None
        return silk - pd.Timedelta(days=half), silk + pd.Timedelta(days=CORN_WINDOW_DAYS - half - 1), f"silking est. {silk.date()} ({SILK_GDD_FROM_GREENUP:.0f} °C GDD after green-up), ±7 days", silk, offset
    if crop == "soybeans" and e1.get("peak_date"):
        pk = pd.Timestamp(e1["peak_date"])
        return pk + pd.Timedelta(days=SOY_WINDOW[0]), pk + pd.Timedelta(days=SOY_WINDOW[1]), "pod set to seed fill (NDVI peak −14 to +21 days)", None, None
    return None


def _flag(wp: pd.Series, tp: pd.Series) -> bool:
    n = len(wp)
    return n > 0 and ((wp < DRY_PCT).sum() >= DRY_SHARE * n or (tp > HOT_PCT).sum() >= HOT_SHARE * n)


def _base_rate(wet_pct: pd.Series, tmax_pct: pd.Series, w0: pd.Timestamp, w1: pd.Timestamp) -> float:
    flags = []
    for y in range(CLIMATE_BASELINE[0], CLIMATE_BASELINE[1] + 1):
        a, b = w0.replace(year=y), w1.replace(year=y)
        flags.append(_flag(wet_pct[a:b], tmax_pct[a:b]))
    return float(np.mean(flags))


def run(
    e1_seasons: list[dict], power: pd.DataFrame, smap: pd.Series | None = None, esi: pd.DataFrame | None = None,
    usdm: pd.DataFrame | None = None,
) -> tuple[list[StressSeason], dict]:
    """Engine 2 for one field. power: POWER daily (T2M_MAX, T2M_MIN, PRECTOTCORR, GWETROOT).

    esi: optional ECOSTRESS scenes (sources.ecostress.field_scenes): date, esi, usable.
    usdm: optional weekly Drought Monitor county statistics (sources.usdm.fetch); display only.
    """
    esi_ok = esi[esi["usable"]] if esi is not None and len(esi) else None
    esi_years = set(esi["date"].dt.year) if esi is not None and len(esi) else set()
    esi_base = None
    if esi_ok is not None and len(esi_ok):
        md = esi_ok["date"].dt.month * 100 + esi_ok["date"].dt.day
        summer = esi_ok[(md >= 615) & (md <= 831)]
        esi_base = float(summer["esi"].median()) if len(summer) else None
    wet_pct = doy_percentile(power["GWETROOT"].rename("gwetroot"))
    tmax_pct = doy_percentile(power["T2M_MAX"].rename("tmax"))
    smap_pct = doy_percentile(smap.rename("smap"), baseline=(2015, 2025)) if smap is not None and len(smap) else None

    # relative vigour baselines: this field's median peak NDVI per crop, excluding uncertain peaks
    by_crop: dict[str, list[tuple[float, float | None]]] = {}
    for s in e1_seasons:
        if s.get("crop") and s.get("peak_ndvi") is not None and not s.get("peak_uncertain"):
            by_crop.setdefault(s["crop"], []).append((s["peak_ndvi"], s.get("integrated_ndvi")))
    medians = {}
    for c, v in by_crop.items():
        ints = [i for _, i in v if i is not None]
        medians[c] = (float(np.median([p for p, _ in v])), float(np.median(ints)) if ints else None, len(v))

    out: list[StressSeason] = []
    for e1 in e1_seasons:
        st = StressSeason(season=e1["season"], crop=e1.get("crop"), peak_ndvi=e1.get("peak_ndvi"))
        w = _window(e1, power)
        if w is None:
            st.note = "no sensitive window: crop not modelled or Engine 1 timing missing"
            out.append(st)
            continue
        w0, w1, basis, silk, offset = w
        st.window_start, st.window_end, st.window_basis = w0.date().isoformat(), w1.date().isoformat(), basis
        st.silking_est = silk.date().isoformat() if silk is not None else None
        st.peak_minus_silking_days = offset
        wp, tp = wet_pct[w0:w1], tmax_pct[w0:w1]
        n = len(wp)
        st.window_days, st.dry_days, st.hot_days = n, int((wp < DRY_PCT).sum()), int((tp > HOT_PCT).sum())
        st.rain_mm = round(float(power.loc[w0:w1, "PRECTOTCORR"].sum()), 1)
        st.gwetroot_mean_pct, st.tmax_mean_pct = round(float(wp.mean()), 0), round(float(tp.mean()), 0)
        if st.dry_days >= DRY_SHARE * n:
            st.drivers.append(f"root-zone wetness below 20th percentile on {st.dry_days} of {n} days")
        if st.hot_days >= HOT_SHARE * n:
            st.drivers.append(f"Tmax above 80th percentile on {st.hot_days} of {n} days")
        st.stress_flag = bool(st.drivers)
        st.base_rate = round(_base_rate(wet_pct, tmax_pct, w0, w1), 3)
        if smap_pct is not None:
            sp = smap_pct[w0:w1]
            if len(sp) >= 0.8 * n:
                st.smap_dry_days = int((sp < DRY_PCT).sum())
                st.smap_agrees = (st.smap_dry_days >= DRY_SHARE * len(sp)) == (st.dry_days >= DRY_SHARE * n)
        if usdm is not None and len(usdm):
            u = usdm_window(usdm, w0, w1)
            if u["maps"]:
                st.usdm_category = u["category"]
                st.usdm_d0_pct, st.usdm_d1_pct, st.usdm_d2_pct = u["d0_pct"], u["d1_pct"], u["d2_pct"]
                st.usdm_agrees = u["dry_d1"] == (st.dry_days >= DRY_SHARE * n)
        med = medians.get(st.crop or "")
        if med:
            st.crop_median_peak, st.crop_n = round(med[0], 3), med[2]
        if e1.get("peak_uncertain") or med is None or st.peak_ndvi is None:
            st.vigour = "uncertain"
        else:
            d_peak = st.peak_ndvi - med[0]
            integ = e1.get("integrated_ndvi")
            d_int = (integ - med[1]) / med[1] if integ is not None and med[1] else None
            st.integrated_rel = round(d_int, 3) if d_int is not None else None
            below = d_peak <= -VIGOUR_BAND or (d_int is not None and d_int <= -INTEGRATED_BAND)
            above = d_peak >= VIGOUR_BAND and (d_int is None or d_int >= INTEGRATED_BAND)
            st.vigour = "below" if below else "above" if above else "similar"
        if st.stress_flag and st.vigour == "below":
            st.scenario = "A: stress at the sensitive stage, with lower vigour"
        elif st.stress_flag and st.vigour in ("similar", "above"):
            st.scenario = "B: regional stress, field vigour held (buffered)"
        elif not st.stress_flag and st.vigour == "below":
            st.scenario = "C: lower vigour without a stress signal (field check)"
        elif st.stress_flag:
            st.scenario = "stress flagged; vigour uncertain"
        else:
            st.scenario = "no stress signal"
        e1_conf = e1.get("confidence", "low")
        st.confidence = CONF_ORDER[min(CONF_ORDER.index(e1_conf), CONF_ORDER.index("moderate"))]
        if esi_base is not None and st.season in esi_years:
            near = esi_ok[(esi_ok["date"] >= w0 - pd.Timedelta(days=ESI_PAD_DAYS)) & (esi_ok["date"] <= w1 + pd.Timedelta(days=ESI_PAD_DAYS))]
            st.esi_scenes, st.esi_field_median = len(near), round(esi_base, 3)
            if len(near) >= ESI_MIN_SCENES:
                st.esi_median = round(float(near["esi"].median()), 3)
                low = st.esi_median <= esi_base - ESI_LOW_DROP
                st.esi_status = "low" if low else "not low"
                st.esi_agrees = low == st.stress_flag
                if st.stress_flag and low and e1_conf != "low":
                    st.confidence = "moderate–high"
                elif st.stress_flag and not low:
                    st.note = "field-scale ESI did not show stress in this window (regional flag not confirmed at 70 m)"
                elif not st.stress_flag and low:
                    st.note = "field-scale ESI was low with no regional flag: field-level stress the regional data missed"
            else:
                st.esi_status = "insufficient"
        out.append(st)
    return out, summarise(out)


def chance_at_least(k: int, base_rates: list[float]) -> float | None:
    """P(at least k flags) if each season were flagged independently at its base rate (Poisson-binomial)."""
    if not base_rates:
        return None
    dist = np.array([1.0])
    for p in base_rates:
        dist = np.convolve(dist, [1 - p, p])
    return float(dist[k:].sum())


def summarise(seasons: list[StressSeason]) -> dict:
    res: dict = {}
    windows = [s for s in seasons if s.window_start]
    flagged = [s.season for s in windows if s.stress_flag]
    res["all_seasons"] = {
        "seasons": len(windows),
        "stress_seasons": len(flagged),
        "stress_years": flagged,
        "expected_stress_seasons": round(sum(s.base_rate or 0 for s in windows), 1),
        "chance_at_least_observed": round(chance_at_least(len(flagged), [s.base_rate or 0 for s in windows]) or 0, 3),
        "note": "regional weather (NASA POWER ~0.5° cells; nearby fields see near-identical conditions): which crop is hit depends on rotation phase",
    }
    assessed = [s for s in windows if s.esi_status in ("low", "not low")]
    res["esi"] = {
        "assessed_seasons": len(assessed),
        "agree": sum(bool(s.esi_agrees) for s in assessed),
        "confirmed_flags": [s.season for s in assessed if s.stress_flag and s.esi_status == "low"],
        "unconfirmed_flags": [s.season for s in assessed if s.stress_flag and s.esi_status == "not low"],
        "field_only_low": [s.season for s in assessed if not s.stress_flag and s.esi_status == "low"],
        "insufficient": [s.season for s in windows if s.esi_status == "insufficient"],
    }
    checked = [s for s in windows if s.smap_agrees is not None]
    res["smap"] = {
        "checked_seasons": len(checked),
        "agree": sum(bool(s.smap_agrees) for s in checked),
        "years": [s.season for s in checked],
        "disagree_years": [s.season for s in checked if not s.smap_agrees],
        "note": "SMAP L4 is 9 km and assimilated: it cross-checks POWER's modelled wetness, it is not a field measurement",
    }
    um = [s for s in windows if s.usdm_category is not None]
    dry = [s for s in um if s.dry_days >= DRY_SHARE * (s.window_days or 0)]
    d1 = [s for s in um if (s.usdm_d1_pct or 0) >= 50]
    res["usdm"] = {
        "checked_seasons": len(um),
        "power_dry_calls": len(dry),
        "dry_calls_at_d0_or_worse": sum((s.usdm_d0_pct or 0) >= 50 for s in dry),
        "dry_calls_at_d1_or_worse": sum((s.usdm_d1_pct or 0) >= 50 for s in dry),
        "d1_windows": len(d1),
        "d1_windows_missed": [s.season for s in d1 if s.dry_days < DRY_SHARE * (s.window_days or 0)],
        "note": "U.S. Drought Monitor, county-scale weekly expert synthesis (NDMC, USDA, NOAA); display only, never changes a flag or confidence",
    }
    for crop in sorted({s.crop for s in seasons if s.crop and s.window_start}):
        cs = [s for s in seasons if s.crop == crop and s.window_start]
        stressed = [s.season for s in cs if s.stress_flag]
        res[crop] = {
            "seasons": len(cs),
            "stress_seasons": len(stressed),
            "stress_years": stressed,
            "expected_stress_seasons": round(sum(s.base_rate or 0 for s in cs), 1),
            "chance_at_least_observed": round(chance_at_least(len(stressed), [s.base_rate or 0 for s in cs]) or 0, 3),
            "dry_years": [s.season for s in cs if any("wetness" in d for d in s.drivers)],
            "hot_years": [s.season for s in cs if any("Tmax" in d for d in s.drivers)],
            "scenario_a_years": [s.season for s in cs if s.scenario.startswith("A")],
            "scenario_b_years": [s.season for s in cs if s.scenario.startswith("B")],
            "scenario_c_years": [s.season for s in cs if s.scenario.startswith("C")],
        }
        if crop == "corn":
            offs = [s.peak_minus_silking_days for s in cs if s.peak_minus_silking_days is not None]
            res[crop]["median_peak_minus_silking_days"] = float(np.median(offs)) if offs else None
    return res


def to_records(seasons: list[StressSeason]) -> list[dict]:
    return [asdict(s) for s in seasons]
