"""App smoke tests: the shell renders on the committed processed data, and the constraint/priority rules hold."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")


def _run() -> AppTest:
    return AppTest.from_file(APP, default_timeout=60).run()


def _option_table(at: AppTest):
    """The side-by-side table: columns '#rank Label', rows = criteria in priority order. Returns it keyed by plain label."""
    df = next(d.value for d in at.dataframe if d.value.index.name == "Criterion (your priority order)")
    return df.rename(columns=lambda c: c.split(" ", 1)[1])


def test_app_renders_without_exceptions():
    at = _run()
    assert not at.exception, at.exception
    titles = [t.value for t in at.title]
    assert "Field Shift" in titles
    assert any(v.startswith("Field A") for v in titles)


def test_constraint_removes_small_grain_option():
    at = _run()
    at.checkbox(key="c_small_grain_market").check().run()
    assert not at.exception
    cards = [m.value for m in at.markdown if m.value.startswith("#### ")]
    assert "#### :gray[Oats + red clover]" in cards  # shown as ruled out, not silently dropped
    assert "Oats + red clover" not in _option_table(at).columns


def test_v9_priorities_reorder_columns_not_ratings():
    at = _run()
    before = _option_table(at)
    at.multiselect[0].set_value(["Crop diversity", "Soil protection"]).run()
    assert not at.exception
    after = _option_table(at)
    assert after.index[0] == "Crop diversity"
    assert set(after.index) == set(before.index)
    for row in before.index:
        assert before.loc[row].to_dict() == after.loc[row].to_dict()  # same rating for every option
