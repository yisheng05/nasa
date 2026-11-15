"""Drought Monitor window summary: overlap of weekly maps with a sensitive window."""

import pandas as pd

from pipeline.sources import usdm


def _maps():
    starts = pd.date_range("2022-07-05", periods=6, freq="7D")  # Tuesdays
    return pd.DataFrame({
        "valid_start": starts,
        "valid_end": starts + pd.Timedelta(days=6, hours=23, minutes=59),
        "none": [100, 40, 0, 0, 100, 100],
        "d0": [0, 60, 100, 100, 0, 0],
        "d1": [0, 20, 80, 70, 0, 0],
        "d2": [0, 0, 10, 0, 0, 0],
        "d3": 0, "d4": 0,
    })


def test_window_overlap_and_dry_calls():
    s = usdm.window_stats(_maps(), "2022-07-14", "2022-07-31")  # overlaps maps 2-4 (weeks of 12, 19, 26 Jul)
    assert s["maps"] == 3
    assert s["d1_pct"] == round((20 + 80 + 70) / 3, 1) and s["dry_d1"] is True and s["dry_d0"] is True
    assert usdm.window_stats(_maps(), "2022-08-09", "2022-08-15")["dry_d0"] is False


def test_window_without_maps():
    assert usdm.window_stats(_maps(), "2019-07-01", "2019-07-14") == {
        "maps": 0, "d0_pct": None, "d1_pct": None, "d2_pct": None, "dry_d1": None, "dry_d0": None}
