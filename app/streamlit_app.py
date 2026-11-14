"""Field Shift: Streamlit shell (handoff §13.1).

Reads only precomputed files in data/processed/. Views that depend on Engines 1-3
show a clear "pending" state instead of placeholder numbers.

Run from the repo root:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import charts
from app import data as D

st.set_page_config(page_title="Field Shift", page_icon="🌱", layout="wide")


# ---------------------------------------------------------------- loaders
@st.cache_data
def _static(fid: str) -> dict:
    return D.load_static(fid)


@st.cache_data
def _power(fid: str) -> pd.DataFrame:
    return D.load_power(fid)


@st.cache_data
def _hls(fid: str) -> pd.DataFrame | None:
    return D.load_hls(fid)


@st.cache_data
def _engine1(fid: str) -> dict | None:
    return D.load_engine1(fid)


@st.cache_data
def _engine2(fid: str) -> dict | None:
    return D.load_engine2(fid)


@st.cache_data
def _smooth(fid: str) -> pd.Series | None:
    return D.load_smooth(fid)


@st.cache_data
def _props() -> dict:
    return D.demo_props()


FIELDS = D.field_ids()
if not FIELDS:
    st.error("No precomputed fields in data/processed/. Run notebooks/01_precompute.ipynb first.")
    st.stop()
PROPS = _props()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.title("Field Shift")
    st.caption("Rotation options from a field's own history")
    fid = st.selectbox("Field", FIELDS, format_func=lambda f: D.field_label(f, _static(f), PROPS.get(f, {})))
    st.subheader("Your priorities")
    priorities = st.multiselect(
        "Pick in order of importance",
        D.PRIORITIES,
        default=["Soil protection", "Water and stress risk", "Workload and simplicity"],
        help="The order you pick sets the row order in Rotation options. It never changes the evidence or the ratings (test V9).",
    )
    st.subheader("Constraints")
    active = {k for k, label in D.CONSTRAINTS.items() if st.checkbox(label, key=f"c_{k}")}
    rented = st.checkbox(D.LONG_TERM_NOTE)

static, power, hls = _static(fid), _power(fid), _hls(fid)
e1, smooth = _engine1(fid), _smooth(fid)
e2 = _engine2(fid)
props = PROPS.get(fid, {})

# farmer edits take precedence over CDL (handoff §8.1)
seq_key = f"seq_{fid}"
if seq_key not in st.session_state:
    st.session_state[seq_key] = D.crop_sequence(static)[["season", "crop", "source"]]
seq = st.session_state[seq_key]

with st.sidebar:
    st.subheader("Data status")
    status = [
        ("Crop history", "USDA CDL 2016–2025", True),
        ("Soil", "USDA SSURGO", True),
        ("Slope", "NASADEM (NASA SRTM), V12 passed", True),
        ("Weather and root-zone wetness", "NASA POWER 1981–2025", True),
        ("Greenness", "NASA HLS 30 m via AppEEARS", hls is not None),
        ("Engine 1 · cover days", f"HLS: {D.coverage_text(e1)}" if e1 else "waiting for HLS", e1 is not None),
        ("Engine 2 · stress windows", "POWER (SMAP L4 pending)" if e2 and "SMAP" not in e2["source"] else "POWER, SMAP L4", e2 is not None),
        ("Engine 3 · ratings", "Engines 1–2, soil, catalogue", False),
    ]
    for name, src, ok in status:
        st.markdown(f"{'✅' if ok else '⏳'} **{name}**  \n<span style='color:#52514e;font-size:0.85em'>{src}</span>", unsafe_allow_html=True)

# ---------------------------------------------------------------- header
letter = fid.split("_")[-1].upper()
st.title(f"Field {letter}, {props.get('county', '')}")
st.markdown("It's November. This field has alternated corn and soybean for ten seasons, and the farmer is planning the next ones.")

soil = static["soil"]
terrain = static["terrain"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Area", f"{static['area_ha']['value']} ha", help=static["area_ha"]["source"])
c2.metric("Interior pixels (30 m)", f"~{static['interior_pixels_approx']['value']}", help="After a one-pixel inward buffer. V1 needs ≥ 50 valid pixels per date.")
c3.metric("Mean slope", f"{terrain['mean_slope_pct']['value']}%", help=f"{terrain['mean_slope_pct']['source']}. Smoothed (σ 1.5 px); 3DEP lidar reference {terrain['ref_3dep_10m_pct']['value']}%.")
c4.metric("Available water, top 100 cm", f"{soil['aws0100wta']['value']:.1f} cm", help=soil["aws0100wta"]["source"])
st.caption(
    f"Soil: {soil['muname']['value']} is the largest map unit ({soil['dominant_share']['value']:.0%}); "
    f"drainage by area: {soil['drclassdcd']['value'].lower()}. Source: {soil['muname']['source']}."
)

t_hist, t_cond, t_rot, t_inputs, t_sum = st.tabs(["Field history", "Changing conditions", "Rotation options", "Your inputs", "Summary"])

# ---------------------------------------------------------------- field history
with t_hist:
    if e1:
        sm, sens = e1["summary"], e1["sensitivity_no_living_cover_months"]
        m1, m2, m3 = st.columns(3)
        m1.metric("No living cover", f"~{sm['no_living_cover_months_per_year']} months a year", help=f"{e1['source']}. Mean over {sm['complete_cover_years']} complete cover years; any green vegetation counts as living cover.")
        m2.metric("Spring green before the crop", f"{sm['spring_green_seasons']} of {sm['spring_assessable_seasons']} springs", help="Springs with ≥ 2 clear scenes 15 Mar–30 Apr. Green may be a cover crop, weeds or volunteers: confirm before crediting.")
        m3.metric("Autumn green after the crop", f"{sm['autumn_green_seasons']} of {len(e1['seasons'])} seasons", help="≥ 2 clear observations ≥ 0.40 after the end of living cover. Recorded, not credited as a cover crop.")
        st.caption(
            f"Coverage so far: {D.coverage_text(e1)}. Living-cover threshold NDVI {e1['method']['cover_threshold_ndvi']:.2f} (provisional); "
            f"at 0.35 / 0.40 / 0.45 the headline is {sens['0.35']} / {sens['0.40']} / {sens['0.45']} months a year."
        )
    st.subheader("Ten seasons on one strip")
    st.altair_chart(charts.season_strip(seq, e1["seasons"] if e1 else None, e2["seasons"] if e2 else None), width="stretch", theme=None)
    st.caption("Crop from the USDA Cropland Data Layer unless you edited it under Your inputs. No living cover = months of each cover year (end of one season's living canopy to the next) with no green vegetation; * = partial first year. Stress = regional root-zone dryness and/or heat in the crop's sensitive window (Engine 2; see Changing conditions). Hover a cell for details.")
    if hls is not None:
        st.subheader("Field greenness, every clear satellite pass")
        st.altair_chart(charts.ndvi_scatter(hls, smooth, e1["method"]["cover_threshold_ndvi"] if e1 else None), width="stretch", theme=None)
        cov = ", ".join(f"{s} {g.date.dt.year.min()}–{g.date.dt.year.max()}" for s, g in hls.groupby("sensor"))
        thr = f" Dashed line: living-cover threshold NDVI {e1['method']['cover_threshold_ndvi']:.2f}." if e1 else ""
        st.caption(f"Median NDVI over the field interior, NASA HLS v2.0, 30 m. Coverage so far: {cov} (L30 = Landsat, S30 = ESA Sentinel-2; other AppEEARS tasks still processing). Faded points had fewer than 50 valid pixels after cloud masking (V1). Grey line: Engine 1 smoothed curve.{thr}")
    else:
        st.info("Satellite greenness (NASA HLS, 30 m) is still processing in AppEEARS. Once it lands, this tab shows every clear pass since 2016, then the cover days and spring-cover flags from Engine 1.")
    with st.expander("Show data"):
        st.dataframe(seq, hide_index=True, width="stretch")
        if e1:
            cols = ["season", "crop", "greenup_date", "peak_date", "peak_ndvi", "decline_date", "living_cover_end", "cover_year_days", "living_cover_days", "off_season_living_days", "no_living_cover_share", "spring_green", "autumn_green_obs", "n_obs_apr_oct", "max_gap_apr_oct", "confidence"]
            st.dataframe(pd.DataFrame(e1["seasons"])[cols], hide_index=True, width="stretch")

# ---------------------------------------------------------------- changing conditions
with t_cond:
    st.subheader("How conditions are changing here")
    st.caption(
        "Regional context, not field measurements: NASA POWER covers a ~0.5° cell, and root-zone wetness is modelled (GMAO MERRA-2). "
        "The window 15 Jun–15 Aug is a calendar stand-in for the maize sensitive period; Engine 2 will use each season's estimated silking date. "
        "Grey band: middle 60% of 1991–2020."
    )
    metrics = D.window_metrics(power)
    corn_years = seq.loc[seq.crop == "corn", "season"].tolist()
    cols = st.columns(2)
    for i, (col, (title, unit, src)) in enumerate(D.METRICS.items()):
        with cols[i % 2]:
            band = D.baseline_band(metrics, col)
            st.altair_chart(charts.trend_chart(metrics, col, title, unit, band, corn_years), width="stretch", theme=None)
            st.caption(f"Linear trend 1981–2025: {D.trend_per_decade(metrics, col):+.2f} {unit} per decade (not tested for significance). Source: {src}.")
    st.subheader("Stress at each crop's sensitive stage (Engine 2)")
    if e2:
        sm2 = e2["summary"]
        a = sm2["all_seasons"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Seasons with a dry or hot sensitive window", f"{a['stress_seasons']} of {a['seasons']}", help=e2["source"])
        c2.metric("Expected from 1991–2020", f"{a['expected_stress_seasons']}", help="Sum over seasons of how often the same calendar window was flagged in 1991–2020.")
        c3.metric("Chance of at least this many", f"{a['chance_at_least_observed']:.0%}", help="If each season were flagged independently at its 1991–2020 rate. Small samples: suggestive, not conclusive.")
        lines = []
        for crop in ("corn", "soybeans"):
            if crop in sm2:
                d = sm2[crop]
                lines.append(f"**{crop.capitalize()}:** {d['stress_seasons']} of {d['seasons']} seasons ({', '.join(map(str, d['stress_years'])) or 'none'}), expected {d['expected_stress_seasons']}.")
        st.markdown(" ".join(lines))
        st.caption(
            "Corn window: 14 days around silking, estimated at 400 °C capped GDD after green-up (cross-checked against the NDVI peak). Soybean window: NDVI peak −14 to +21 days. "
            "Flag: root-zone wetness below the 20th percentile on half the window, or Tmax above the 80th percentile on 5 of 14 days (provisional). "
            f"All three demo fields share one POWER cell, so they see the same weather; which crop is hit depends on rotation phase. Confidence capped at moderate. {'SMAP L4 confirmation pending.' if 'SMAP' not in e2['source'] else ''}"
        )
        cols2 = ["season", "crop", "window_start", "window_end", "dry_days", "hot_days", "window_days", "base_rate", "vigour", "scenario", "confidence"]
        st.dataframe(pd.DataFrame(e2["seasons"])[cols2], hide_index=True, width="stretch")
    else:
        st.info("Engine 2 runs once Engine 1 has this field's seasons.")
    with st.expander("Show data"):
        st.dataframe(metrics.round(2), width="stretch")

# ---------------------------------------------------------------- rotation options
with t_rot:
    st.subheader("Rotation options against your priorities")
    kept, dropped = D.apply_constraints(active)
    for name, why in dropped:
        st.warning(f"**{name}** removed: {why}.")
    crit = D.ordered_criteria(priorities)
    table = pd.DataFrame(
        {c["name"]: [("baseline" if i == 0 else "pending") for _ in crit] + ["—" if i == 0 else "pending"] for i, c in enumerate(kept)},
        index=pd.Index([*crit, "Confidence"], name="Criterion (your priority order)"),
    )
    st.dataframe(table, width="stretch")
    order_txt = " → ".join(priorities) if priorities else "no priorities chosen (default order)"
    st.caption(f"Rows follow your priorities: {order_txt}. Ratings will be better / similar / worse relative to the current rotation, each with its evidence and confidence (Engine 3, not built yet). Changing priorities reorders rows; it never changes a rating (V9).")
    if rented:
        st.info("On a short lease, the benefits of cover crops and longer rotations build over years and may not reach the person farming. Check lease terms before choosing.")
    with st.expander("What each rating will use"):
        for k in crit:
            st.markdown(f"**{k}.** {D.CRITERION_EVIDENCE[k]}")
    with st.expander("What this tool cannot establish"):
        st.markdown(
            "- Yield or profit effects on this field.\n- Soil organic carbon, nitrogen, phosphorus, pH, compaction or biology.\n"
            "- Whether winter green is a cover crop or weeds: confirm before crediting it.\n- Field-level moisture: drivers are regional (9 km and ~0.5°)."
        )

# ---------------------------------------------------------------- inputs
with t_inputs:
    left, right = st.columns([3, 2])
    with left:
        st.subheader("Crop history")
        st.caption("Prefilled from CDL. Your entries take precedence and are marked as yours.")
        edited = st.data_editor(
            seq,
            hide_index=True,
            width="stretch",
            disabled=["season", "source"],
            column_config={"crop": st.column_config.SelectboxColumn("crop", options=D.CROP_OPTIONS, required=True)},
            key=f"editor_{fid}",
        )
        cdl = D.crop_sequence(static).set_index("season")["crop"]
        edited["source"] = ["CDL" if cdl.get(s) == c else "farmer" for s, c in zip(edited.season, edited.crop, strict=True)]
        if not edited.equals(st.session_state[seq_key]):
            st.session_state[seq_key] = edited
            st.rerun()
        st.subheader("Soil")
        st.caption("Area-weighted from USDA SSURGO. Replace with your own soil-test values where you have them (not saved yet).")
        st.dataframe(
            pd.DataFrame(
                [
                    {"Property": "Available water, top 100 cm (cm)", "Value": soil["aws0100wta"]["value"]},
                    {"Property": "Surface organic matter (%)", "Value": soil["om_r"]["value"]},
                    {"Property": "Erodibility K factor", "Value": soil["kwfact"]["value"]},
                    {"Property": "Slope, survey (%)", "Value": soil["slopegradwta"]["value"]},
                    {"Property": "Slope, NASADEM smoothed (%)", "Value": terrain["mean_slope_pct"]["value"]},
                ]
            ),
            hide_index=True,
            width="stretch",
        )
    with right:
        st.subheader("Where")
        ring = static["geometry"]["coordinates"][0]
        lon = sum(p[0] for p in ring) / len(ring)
        lat = sum(p[1] for p in ring) / len(ring)
        st.pydeck_chart(
            pdk.Deck(
                layers=[pdk.Layer("PolygonLayer", data=[{"polygon": ring}], get_polygon="polygon", get_fill_color=[42, 120, 214, 50], get_line_color=[42, 120, 214], line_width_min_pixels=2)],
                initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=13.3),
                map_provider="carto",
                map_style="light",
            ),
            height=320,
        )
        st.caption(f"{props.get('naip_note', '')}. Selected because CDL shows strict corn/soybean alternation 2016–2025; checked on NAIP 2025.")

# ---------------------------------------------------------------- summary
with t_sum:
    st.subheader("One page for the agronomist conversation")
    seq_txt = " ".join("C" if c == "corn" else "S" if c == "soybeans" else c[:3] for c in seq.crop)
    md = [
        f"# Field {letter}, {props.get('county', '')}",
        "",
        f"- Area: {static['area_ha']['value']} ha (~{static['interior_pixels_approx']['value']} interior 30 m pixels)",
        f"- Crop sequence 2016–2025: {seq_txt} (USDA CDL{', with farmer edits' if (seq.source == 'farmer').any() else ''})",
        f"- Soil: {soil['muname']['value']} (largest unit); drainage {soil['drclassdcd']['value'].lower()}; available water {soil['aws0100wta']['value']:.1f} cm in the top 100 cm (USDA SSURGO)",
        f"- Mean slope: {terrain['mean_slope_pct']['value']}% (NASADEM, smoothed; lidar reference {terrain['ref_3dep_10m_pct']['value']}%)",
        "",
        "## Your priorities",
        ", ".join(f"{i + 1} {p.lower()}" for i, p in enumerate(priorities)) or "Not set",
        "",
        "## Soil cover (Engine 1, NASA HLS 30 m)",
        (
            f"- No living cover: about {e1['summary']['no_living_cover_months_per_year']} months a year "
            f"({D.coverage_text(e1)}; threshold NDVI {e1['method']['cover_threshold_ndvi']:.2f}, range "
            f"{e1['sensitivity_no_living_cover_months']['0.35']}–{e1['sensitivity_no_living_cover_months']['0.45']})\n"
            f"- Spring green before the crop: {e1['summary']['spring_green_seasons']} of {e1['summary']['spring_assessable_seasons']} assessable springs (confirm before crediting a cover crop)"
            if e1 else "- Pending: HLS still processing"
        ),
        "",
        "## Stress at the sensitive stage (Engine 2, regional)",
        (
            f"- Dry or hot sensitive window in {e2['summary']['all_seasons']['stress_seasons']} of {e2['summary']['all_seasons']['seasons']} seasons "
            f"(expected {e2['summary']['all_seasons']['expected_stress_seasons']} from 1991–2020; chance of at least this many {e2['summary']['all_seasons']['chance_at_least_observed']:.0%})"
            if e2 else "- Pending"
        ),
        "",
        "## Pending",
        *([] if e2 else ["- Stress at the sensitive stage, and how often it recurs (Engine 2)"]),
        "- Rotation ratings with evidence and confidence (Engine 3)",
        "",
        "## Not established by this tool",
        "Yield or profit effects on this field; change in soil carbon or nutrients.",
    ]
    text = "\n".join(md)
    st.markdown(text)
    st.download_button("Download summary (.md)", text, file_name=f"fieldshift_{fid}_summary.md", mime="text/markdown")
