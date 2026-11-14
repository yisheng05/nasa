"""Engine 2 on synthetic weather with known answers (handoff §8.2; V7 determinism)."""

import numpy as np
import pandas as pd
import pytest

from pipeline import engine2 as E2


def _power(dry_year: int | None = None, hot_year: int | None = None, seed: int = 0) -> pd.DataFrame:
    days = pd.date_range("1985-01-01", "2025-12-31", freq="D")
    rng = np.random.default_rng(seed)
    doy = days.dayofyear.to_numpy()
    tmax = 15 + 15 * np.sin((doy - 105) / 365 * 2 * np.pi)  # identical every year: no chance flags
    df = pd.DataFrame(
        {"T2M_MAX": tmax, "T2M_MIN": tmax - 10, "PRECTOTCORR": rng.gamma(0.5, 5, len(days)), "GWETROOT": 0.6},
        index=days,
    )
    if dry_year:
        df.loc[f"{dry_year}-07-01":f"{dry_year}-08-31", "GWETROOT"] = 0.2
    if hot_year:
        df.loc[f"{hot_year}-07-01":f"{hot_year}-08-31", "T2M_MAX"] += 12
    return df


def _e1(season, crop, greenup, peak, peak_ndvi=0.9, integrated=60.0, uncertain=False):
    return {"season": season, "crop": crop, "greenup_date": greenup, "peak_date": peak, "peak_ndvi": peak_ndvi,
            "integrated_ndvi": integrated, "peak_uncertain": uncertain, "confidence": "high"}


def test_doy_percentile_extremes_and_ties():
    rng = np.random.default_rng(1)
    s = _power()["GWETROOT"].rename("g") + rng.normal(0, 0.05, 14975).round(2)
    p = E2.doy_percentile(s)
    assert p.between(0, 100).all()
    low = s.copy()
    low.loc["2010-07-15"] = 0.0
    high = s.copy()
    high.loc["2010-07-15"] = 1.0
    assert E2.doy_percentile(low).loc["2010-07-15"] < 1
    assert E2.doy_percentile(high).loc["2010-07-15"] > 99
    tied = pd.Series(0.5, index=s.index, name="t")
    assert E2.doy_percentile(tied).loc["2010-07-15"] == pytest.approx(50)


def test_corn_silking_from_capped_gdd():
    days = pd.date_range("1985-01-01", "2025-12-31", freq="D")
    pw = pd.DataFrame({"T2M_MAX": 30.0, "T2M_MIN": 20.0, "PRECTOTCORR": 1.0, "GWETROOT": 0.6}, index=days)  # 15 °C GDD per day
    st, _ = E2.run([_e1(2022, "corn", "2022-07-01", "2022-07-30")], pw)
    # 400 / 15 -> day 27 counting green-up as day 1 -> 27 July
    assert st[0].silking_est == "2022-07-27"
    assert (st[0].window_start, st[0].window_end) == ("2022-07-20", "2022-08-02")
    assert st[0].peak_minus_silking_days == 3


def test_soy_window_around_peak():
    st, _ = E2.run([_e1(2021, "soybeans", "2021-06-20", "2021-08-01")], _power())
    assert (st[0].window_start, st[0].window_end) == ("2021-07-18", "2021-08-22")


def test_dry_and_hot_flags():
    seasons = [_e1(2022, "corn", "2022-06-20", "2022-07-25"), _e1(2024, "corn", "2024-06-20", "2024-07-25")]
    dry, _ = E2.run(seasons, _power(dry_year=2022))
    assert dry[0].stress_flag and any("wetness" in d for d in dry[0].drivers)
    assert not dry[1].stress_flag
    hot, _ = E2.run(seasons, _power(hot_year=2024))
    assert hot[1].stress_flag and any("Tmax" in d for d in hot[1].drivers)


def test_scenarios_and_vigour():
    seasons = [
        _e1(2018, "corn", "2018-06-20", "2018-07-25", 0.90, 60.0),
        _e1(2020, "corn", "2020-06-20", "2020-07-25", 0.90, 60.0),
        _e1(2022, "corn", "2022-06-20", "2022-07-25", 0.80, 45.0),  # dry + low vigour -> A
        _e1(2024, "corn", "2024-06-20", "2024-07-25", 0.80, 45.0),  # low vigour, no stress -> C
        _e1(2016, "corn", "2016-06-20", "2016-07-25", 0.90, 60.0, uncertain=True),
    ]
    st, summ = E2.run(seasons, _power(dry_year=2022))
    by = {s.season: s for s in st}
    assert by[2022].scenario.startswith("A") and by[2022].vigour == "below"
    assert by[2024].scenario.startswith("C")
    assert by[2018].scenario == "no stress signal"
    assert by[2016].vigour == "uncertain"
    assert summ["corn"]["stress_years"] == [2022]
    assert summ["corn"]["expected_stress_seasons"] == 0  # no flags in a weather record with no anomalies
    assert all(s.confidence in ("low", "moderate") for s in st)  # capped: regional drivers


def test_v7_deterministic():
    seasons = [_e1(2022, "corn", "2022-06-20", "2022-07-25"), _e1(2021, "soybeans", "2021-06-20", "2021-08-01")]
    a, sa = E2.run(seasons, _power(dry_year=2022))
    b, sb = E2.run(seasons, _power(dry_year=2022))
    assert E2.to_records(a) == E2.to_records(b) and sa == sb


def test_base_rate_with_noisy_weather():
    """Independent daily noise: the heat rule alone fires in roughly 1 year in 8."""
    rng = np.random.default_rng(3)
    pw = _power()
    pw["T2M_MAX"] = pw["T2M_MAX"] + rng.normal(0, 2, len(pw))
    st, _ = E2.run([_e1(2024, "corn", "2024-06-20", "2024-07-25")], pw)
    assert 0.0 < st[0].base_rate < 0.35


def test_chance_at_least():
    assert E2.chance_at_least(0, [0.3, 0.3]) == pytest.approx(1.0)
    assert E2.chance_at_least(2, [0.5, 0.5]) == pytest.approx(0.25)
    assert E2.chance_at_least(3, [0.27] * 5) == pytest.approx(0.126, abs=0.005)


def _esi(year_values: dict[int, float], base: float = 0.55) -> pd.DataFrame:
    """Usable ESI scenes every 4 days, Jun-Sep 2018-2025; chosen years get their value from 20 Jul to 10 Aug."""
    rows = []
    for y in range(2018, 2026):
        for d in pd.date_range(f"{y}-06-01", f"{y}-09-15", freq="4D"):
            v = year_values.get(y, base) if pd.Timestamp(f"{y}-07-15") <= d <= pd.Timestamp(f"{y}-08-10") else base
            rows.append({"date": d, "esi": v, "usable": True})
    return pd.DataFrame(rows)


def test_esi_confirms_flag_and_raises_confidence():
    seasons = [_e1(2022, "corn", "2022-06-20", "2022-07-25"), _e1(2024, "corn", "2024-06-20", "2024-07-25")]
    st, summ = E2.run(seasons, _power(dry_year=2022), esi=_esi({2022: 0.35}))
    by = {s.season: s for s in st}
    assert by[2022].stress_flag and by[2022].esi_status == "low" and by[2022].esi_agrees
    assert by[2022].confidence == "moderate–high"
    assert by[2024].esi_status == "not low" and by[2024].esi_agrees and by[2024].confidence == "moderate"
    assert summ["esi"]["confirmed_flags"] == [2022] and summ["esi"]["agree"] == 2


def test_esi_disagreement_is_reported_not_hidden():
    seasons = [_e1(2022, "corn", "2022-06-20", "2022-07-25"), _e1(2024, "corn", "2024-06-20", "2024-07-25")]
    st, summ = E2.run(seasons, _power(dry_year=2022), esi=_esi({2024: 0.35}))
    by = {s.season: s for s in st}
    assert by[2022].stress_flag and by[2022].esi_status == "not low" and by[2022].esi_agrees is False
    assert by[2022].confidence == "moderate" and "not confirmed" in by[2022].note
    assert by[2024].esi_status == "low" and "missed" in by[2024].note
    assert summ["esi"]["unconfirmed_flags"] == [2022] and summ["esi"]["field_only_low"] == [2024]


def test_esi_needs_enough_scenes_and_years():
    seasons = [_e1(2022, "corn", "2022-06-20", "2022-07-25"), _e1(2016, "corn", "2016-06-20", "2016-07-25")]
    sparse = _esi({}).iloc[::9].reset_index(drop=True)
    st, _ = E2.run(seasons, _power(dry_year=2022), esi=sparse)
    by = {s.season: s for s in st}
    assert by[2022].esi_status == "insufficient"
    assert by[2016].esi_status is None  # before ECOSTRESS (July 2018)
