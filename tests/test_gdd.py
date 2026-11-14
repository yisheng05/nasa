"""V10: capped GDD unit tests (handoff §15)."""

import pytest

from pipeline.gdd import gdd_day


@pytest.mark.parametrize(
    ("tmax", "tmin", "expected"),
    [(35, 18, 14.0), (25, 5, 7.5), (8, 2, 0.0)],
)
def test_v10_capped_gdd(tmax, tmin, expected):
    assert float(gdd_day(tmax, tmin)) == pytest.approx(expected)
