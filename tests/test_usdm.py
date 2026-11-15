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
    s = usdm.window_stats(_maps(), "2019-07-01", "2019-07-14")
    assert s["maps"] == 0 and s["category"] is None and s["dry_d1"] is None


def test_majority_category():
    m = _maps()
    assert usdm.window_stats(m, "2022-07-14", "2022-07-31")["category"] == "D1"  # D1 mean 56.7, D2 3.3
    assert usdm.window_stats(m, "2022-07-12", "2022-07-18")["category"] == "D0"  # 60% D0, 20% D1
    assert usdm.window_stats(m, "2022-08-09", "2022-08-15")["category"] == "None"
    assert set(usdm.CATEGORY_LABELS) == {"None", "D0", "D1", "D2", "D3", "D4"}
