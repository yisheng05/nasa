"""Altair charts. Colours from the validated reference palette (light mode):
corn #eda100 / soybeans #008300 pass CVD checks as a pair; any other crop is a
labelled neutral. Yellow is below 3:1 contrast, so every chart ships visible
labels or a table view. Sensors L30/S30 use slots 1-2 (blue/orange).
"""

from __future__ import annotations

import altair as alt
import pandas as pd

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e6e5e1"
NEUTRAL = "#b9b8b2"
PENDING = "#efeeea"
BLUE, ORANGE, YELLOW, GREEN = "#2a78d6", "#eb6834", "#eda100", "#008300"
CROP_COLOURS = {"corn": YELLOW, "soybeans": GREEN}


def _style(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure(background=SURFACE, font="sans-serif")
        .configure_view(stroke=None)
        .configure_axis(labelColor=INK_2, titleColor=INK_2, gridColor=GRID, domainColor=GRID, tickColor=GRID, labelFontSize=12, titleFontSize=12)
        .configure_legend(labelColor=INK_2, titleColor=INK_2, orient="top", labelFontSize=12, symbolSize=120)
    )


COMPUTED = "#f6f5f2"


def _cover_cell(rec: dict | None) -> tuple[str, str, str]:
    """Label, fill and tooltip for the no-living-cover row."""
    if rec is None:
        return "no data yet", PENDING, "HLS for this season not downloaded or processed yet"
    if rec.get("no_living_cover_share") is None:
        return "—", PENDING, rec.get("note") or "Not enough clear observations"
    months = rec["no_living_cover_share"] * 12
    label = f"{months:.1f} mo" + ("*" if rec.get("cover_year_partial") else "")
    tip = (
        f"No living cover {rec['no_living_cover_days']} of {rec['cover_year_days']} days "
        f"({rec['cover_year_start']} to {rec['cover_year_end']}{', partial year' if rec.get('cover_year_partial') else ''}). "
        f"Green-up {rec['greenup_date']}, peak {rec['peak_date']} (NDVI {rec['peak_ndvi']}{f", uncertain: {rec.get('peak_gap_days')}-day cloudy gap" if rec.get('peak_uncertain') else ''}), end of living cover {rec['living_cover_end']}. "
        f"Off-season living days {rec.get('off_season_living_days')}. Spring: {rec['spring_green']}. Confidence {rec['confidence']}."
    )
    return label, COMPUTED, tip


def _esi_text(rec: dict) -> str:
    s = rec.get("esi_status")
    if s is None:
        return ""
    if s == "insufficient":
        return f"Field-scale ECOSTRESS: too few clear scenes ({rec.get('esi_scenes', 0)}). "
    agree = "agrees with" if rec.get("esi_agrees") else "differs from"
    return f"Field-scale ECOSTRESS stress index {rec['esi_median']} over {rec['esi_scenes']} scenes ({s} against this field's {rec['esi_field_median']}); {agree} the regional flag. "


def _stress_cell(rec: dict | None) -> tuple[str, str, str]:
    if rec is None:
        return "pending", PENDING, "Engine 2 not run for this season yet"
    if not rec.get("window_start"):
        return "—", PENDING, rec.get("note") or "No sensitive window"
    kinds = (["dry"] if any("wetness" in d for d in rec["drivers"]) else []) + (["hot"] if any("Tmax" in d for d in rec["drivers"]) else [])
    label = "+".join(kinds) if kinds else "none"
    tip = (
        f"Sensitive window {rec['window_start']} to {rec['window_end']} ({rec['window_basis']}). "
        f"Root-zone wetness < p20 on {rec['dry_days']} of {rec['window_days']} days; Tmax > p80 on {rec['hot_days']}. "
        f"Flagged in {rec['base_rate']:.0%} of 1991–2020 years for the same dates. Vigour {rec['vigour']}. {rec['scenario']}. "
        + _esi_text(rec)
        + f"Confidence {rec['confidence']}."
    )
    return label, COMPUTED, tip


def season_strip(seq: pd.DataFrame, e1_seasons: list[dict] | None = None, e2_seasons: list[dict] | None = None) -> alt.Chart:
    """Ten seasons on one strip: crop (CDL or farmer), no living cover (Engine 1), stress window (Engine 2)."""
    by_year = {r["season"]: r for r in (e1_seasons or [])}
    by_year2 = {r["season"]: r for r in (e2_seasons or [])}
    rows = []
    for r in seq.itertuples():
        rows.append({"season": str(r.season), "row": "Crop", "label": r.crop.replace("soybeans", "soy"), "fill": CROP_COLOURS.get(r.crop, NEUTRAL), "tip": f"{r.crop} · source {r.source}", "ink": "#ffffff" if r.crop == "soybeans" else INK})
        label, fill, tip = _cover_cell(by_year.get(r.season))
        rows.append({"season": str(r.season), "row": "No living cover", "label": label, "fill": fill, "tip": tip, "ink": INK if fill == COMPUTED else INK_2})
        label2, fill2, tip2 = _stress_cell(by_year2.get(r.season))
        rows.append({"season": str(r.season), "row": "Stress at sensitive stage", "label": label2, "fill": fill2, "tip": tip2, "ink": INK if fill2 == COMPUTED else INK_2})
    df = pd.DataFrame(rows)
    order = ["Crop", "No living cover", "Stress at sensitive stage"]
    base = alt.Chart(df).encode(
        x=alt.X("season:O", title=None, axis=alt.Axis(orient="top", labelAngle=0, domain=False, ticks=False)),
        y=alt.Y("row:N", title=None, sort=order, axis=alt.Axis(domain=False, ticks=False, labelLimit=220)),
    )
    cells = base.mark_rect(cornerRadius=4, stroke=SURFACE, strokeWidth=2).encode(
        color=alt.Color("fill:N", scale=None, legend=None), tooltip=[alt.Tooltip("season:O", title="Season"), alt.Tooltip("row:N", title="Row"), alt.Tooltip("tip:N", title="Detail")]
    )
    text = base.mark_text(fontSize=12).encode(text="label:N", color=alt.Color("ink:N", scale=None, legend=None))
    return _style((cells + text).properties(height=150))


def ndvi_scatter(obs: pd.DataFrame, smooth: pd.Series | None = None, threshold: float | None = None) -> alt.Chart:
    d = obs.copy()
    d["Sensor"] = d["sensor"].map({"L30": "Landsat (L30)", "S30": "Sentinel-2 (S30)"})
    d["kept"] = d["passes_v1"].map({True: "Kept (≥ 50 valid px)", False: "Dropped (V1)"})
    sel = alt.selection_point(nearest=True, on="pointerover", fields=["date"], empty=False)
    domain, rng = ["Landsat (L30)", "Sentinel-2 (S30)"], [BLUE, ORANGE]
    layers = []
    if smooth is not None:
        domain, rng = [*domain, "Smoothed (Engine 1)"], [*rng, INK_2]
        sm = smooth.rename("ndvi").reset_index().rename(columns={"index": "date"})
        sm.columns = ["date", "ndvi"]
        sm["Sensor"] = "Smoothed (Engine 1)"
        layers.append(alt.Chart(sm).mark_line(strokeWidth=2).encode(x="date:T", y="ndvi:Q", color=alt.Color("Sensor:N", scale=alt.Scale(domain=domain, range=rng), legend=alt.Legend(title=None))))
    if threshold is not None:
        th = pd.DataFrame({"y": [threshold]})
        layers.append(alt.Chart(th).mark_rule(color=INK_2, strokeDash=[4, 4], strokeWidth=1).encode(y="y:Q", tooltip=[alt.Tooltip("y:Q", title="Living-cover threshold")]))
    pts = alt.Chart(d).mark_circle(size=70, stroke=SURFACE, strokeWidth=2).encode(
        x=alt.X("date:T", title=None),
        y=alt.Y("ndvi_median:Q", title="Field median NDVI", scale=alt.Scale(domain=[-0.1, 1.0])),
        color=alt.Color("Sensor:N", scale=alt.Scale(domain=domain, range=rng), legend=alt.Legend(title=None)),
        opacity=alt.condition(alt.datum.passes_v1, alt.value(0.9), alt.value(0.15)),
        tooltip=[alt.Tooltip("date:T", title="Date"), alt.Tooltip("Sensor:N"), alt.Tooltip("ndvi_median:Q", title="NDVI median", format=".2f"), alt.Tooltip("n_valid:Q", title="Valid pixels"), alt.Tooltip("kept:N", title="V1")],
    ).add_params(sel)
    rule = alt.Chart(d).mark_rule(color=INK_2, strokeWidth=1).encode(x="date:T").transform_filter(sel)
    return _style(alt.layer(*layers, pts, rule).properties(height=300))


def trend_chart(metrics: pd.DataFrame, col: str, title: str, unit: str, band: dict, corn_years: list[int]) -> alt.Chart:
    d = metrics[[col]].reset_index().rename(columns={col: "value"})
    d["series"] = "All years"
    corn = d[d.year.isin(corn_years)].assign(series="Corn seasons on this field")
    colour = alt.Color("series:N", scale=alt.Scale(domain=["All years", "Corn seasons on this field"], range=[BLUE, YELLOW]), legend=alt.Legend(title=None))
    xscale = alt.Scale(domain=[1981, int(d.year.max())], zero=False, nice=False)
    x = alt.X("year:Q", title=None, axis=alt.Axis(format="d", tickCount=8), scale=xscale)
    y = alt.Y("value:Q", title=unit, scale=alt.Scale(zero=False))
    bandf = pd.DataFrame([{"x0": 1981, "x1": int(d.year.max()), "lo": band["p20"], "hi": band["p80"]}])
    band_l = alt.Chart(bandf).mark_rect(color=NEUTRAL, opacity=0.25).encode(
        x=alt.X("x0:Q", scale=xscale, title=None), x2="x1:Q", y=alt.Y("lo:Q", scale=alt.Scale(zero=False)), y2="hi:Q"
    )
    line = alt.Chart(d).mark_line(strokeWidth=2).encode(x=x, y=y, color=colour)
    hover = alt.selection_point(nearest=True, on="pointerover", fields=["year"], empty=False)
    hit = alt.Chart(d).mark_circle(size=200, opacity=0).encode(
        x=x, y=y, tooltip=[alt.Tooltip("year:Q", title="Year", format="d"), alt.Tooltip("value:Q", title=title, format=".2f")]
    ).add_params(hover)
    rule = alt.Chart(d).mark_rule(color=INK_2, strokeWidth=1).encode(x=x).transform_filter(hover)
    dots = alt.Chart(corn).mark_circle(size=90, stroke=SURFACE, strokeWidth=2, opacity=1).encode(
        x=x, y=y, color=colour, tooltip=[alt.Tooltip("year:Q", title="Corn season", format="d"), alt.Tooltip("value:Q", title=title, format=".2f")]
    )
    return _style((band_l + line + hit + rule + dots).properties(title=alt.TitleParams(title, anchor="start", color=INK, fontSize=13, fontWeight="normal"), height=220))
