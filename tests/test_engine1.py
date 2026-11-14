"""Engine 1 on synthetic seasons with known answers (handoff §8.1; V7 determinism)."""

import numpy as np
import pandas as pd
import pytest

from pipeline import engine1 as E

YEARS = [2018, 2019, 2020]
BASE, PEAK = 0.22, 0.88


def _truth(day_index: pd.DatetimeIndex, rye: bool = False) -> pd.Series:
    """Double-logistic season per year: rise centred 20 Jun, fall centred 10 Sep."""
    v = np.full(len(day_index), BASE)
    for y in YEARS:
        t = (day_index - pd.Timestamp(f"{y}-01-01")).days.to_numpy()
        rise = 1 / (1 + np.exp(-(t - 171) / 6))  # 20 Jun = day 171
        fall = 1 / (1 + np.exp((t - 253) / 6))  # 10 Sep = day 253
        v += (PEAK - BASE) * rise * fall
        if rye:
            v += 0.35 * np.exp(-0.5 * ((t - 100) / 12) ** 2)  # green bump around 10 Apr
    return pd.Series(v, index=day_index)


def _obs(rye: bool = False, every: int = 8) -> pd.DataFrame:
    days = pd.date_range(f"{YEARS[0]}-01-01", f"{YEARS[-1]}-12-31", freq="D")
    truth = _truth(days, rye)
    dates = days[::every]
    return pd.DataFrame({"date": dates, "ndvi_median": truth[dates].to_numpy(), "passes_v1": True, "sensor": "L30", "n_valid": 400})


CROPS = {2018: "corn", 2019: "soybeans", 2020: "corn"}


def test_greenup_and_decline_timing():
    seasons, _ = E.run(_obs(), CROPS, YEARS)
    for s in seasons:
        g = pd.Timestamp(s.greenup_date)
        d = pd.Timestamp(s.decline_date)
        assert abs((g - pd.Timestamp(f"{s.season}-06-20")).days) <= 5
        assert abs((d - pd.Timestamp(f"{s.season}-09-10")).days) <= 5
        assert s.peak_ndvi == pytest.approx(PEAK, abs=0.05)


def test_living_cover_days_match_truth():
    seasons, _ = E.run(_obs(), CROPS, YEARS)
    days = pd.date_range(f"{YEARS[0]}-01-01", f"{YEARS[-1]}-12-31", freq="D")
    truth = _truth(days)
    for s in seasons[1:]:
        expected = int((truth[s.cover_year_start : s.cover_year_end] >= E.COVER_THRESHOLD).sum())
        assert s.living_cover_days == pytest.approx(expected, abs=6)


def test_spring_green_detected_only_when_present():
    with_rye, _ = E.run(_obs(rye=True), CROPS, YEARS)
    without, _ = E.run(_obs(rye=False), CROPS, YEARS)
    assert all(s.spring_green.startswith("green detected") for s in with_rye)
    assert all(s.spring_green == "none detected" for s in without)
    assert all((s.off_season_living_days or 0) > 0 for s in with_rye[1:])


def test_spring_verdict_needs_core_window_observations():
    o = _obs(rye=True)
    o = o[~o.date.dt.month.isin([3, 4])]  # no clear scenes in March-April
    seasons, _ = E.run(o, CROPS, YEARS)
    assert all(s.spring_green == "insufficient data" for s in seasons)


def test_no_cover_invented_across_winter_gap():
    """A green December observation must not carry living cover through an unobserved winter."""
    o = _obs()
    o = o[~((o.date >= "2018-12-10") & (o.date <= "2019-04-15"))]
    extra = pd.DataFrame({"date": [pd.Timestamp("2018-12-05")], "ndvi_median": [0.6], "passes_v1": [True], "sensor": ["L30"], "n_valid": [400]})
    o = pd.concat([o, extra]).sort_values("date")
    _, z = E.run(o, CROPS, YEARS)
    living = E.living_mask(o[o.passes_v1], z)
    assert not living["2019-01-05":"2019-04-15"].any()


def test_no_overshoot_across_cloudy_peak():
    """A 40-day gap at the peak must not push the curve above the clear observations (2021 on Field A)."""
    o = _obs(every=7)
    o = o[~((o.date >= "2019-06-25") & (o.date <= "2019-08-05"))]
    _, z = E.run(o, CROPS, YEARS)
    seen = o[o.date.dt.year == 2019].ndvi_median.max()
    assert z["2019-04-01":"2019-10-31"].max() <= seen + E.PEAK_CAP_TOL + 1e-9


def test_v7_deterministic():
    a, za = E.run(_obs(rye=True), CROPS, YEARS)
    b, zb = E.run(_obs(rye=True), CROPS, YEARS)
    assert E.to_records(a) == E.to_records(b)
    assert za.equals(zb)
