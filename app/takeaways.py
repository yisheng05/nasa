"""The deck's messages and the farmer's next steps, built only from the evidence JSON (V8).

Shared by the Streamlit app and the standalone page (app/build_web.py embeds the static
parts; the page mirrors `priority_action` in JavaScript, checked by tests/test_web_parity.py).
"""

from __future__ import annotations

import re
from datetime import date

from pipeline import engine3 as E3
from pipeline.config import PROCESSED

DECISION = ("Should the next rotation stay the same, add a cereal rye cover, or add oats and red clover? "
            "The tool shows the evidence; the choice stays with the farmer.")
SIGNIFICANT_P = 0.05
# plain names for the three options (as on slide 5), what each changes, and how to say it in a sentence
OPTIONS = {
    "cso_rc": {"label": "Oats + red clover", "blurb": "Corn, soybean, then oats with red clover sown under them: a three-year rotation.",
               "phrase": "adding oats + red clover"},
    "cs_rye": {"label": "Cereal rye cover", "blurb": "The same corn–soybean, with cereal rye sown after harvest and ended in spring.",
               "phrase": "adding a cereal rye cover"},
    "cs": {"label": "Current rotation", "blurb": "Corn–soybean as today. The other options are rated against it.",
           "phrase": "keeping the current rotation"},
}
GREEN_MIN_OBS = 2  # Engine 1's autumn-green rule: >= 2 clear observations >= 0.40 after the end of living cover


def _day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.day} {d:%B}"


def window_span(e2: dict) -> tuple[str, str]:
    """Earliest start and latest end of the sensitive windows by calendar day, across all seasons."""
    md0 = min(s["window_start"][5:] for s in e2["seasons"] if s.get("window_start"))
    md1 = max(s["window_end"][5:] for s in e2["seasons"] if s.get("window_end"))
    return _day(f"2001-{md0}"), _day(f"2001-{md1}")


def _join(xs: list) -> str:
    xs = [str(x) for x in xs]
    return ", ".join(xs[:-1]) + (" and " if len(xs) > 1 else "") + xs[-1] if xs else ""


def green_after_harvest(e1: dict) -> dict:
    """Seasons whose harvest was followed by green (Engine 1 autumn green), split by crop."""
    out = {}
    for crop in ("corn", "soybeans"):
        ss = [s for s in e1["seasons"] if s.get("crop") == crop]
        out[crop] = {"years": [s["season"] for s in ss if (s.get("autumn_green_obs") or 0) >= GREEN_MIN_OBS], "n": len(ss)}
    return out


def cross_fields(fields: list[tuple[str, dict, dict]]) -> dict:
    """Across the demo fields: green after corn harvest, and which crop each stress year hit.

    fields: (letter, engine1 doc, engine2 doc) per field.
    """
    green, hits, years = [], [], set()
    for letter, e1, e2 in fields:
        g = green_after_harvest(e1)["corn"]
        green.append({"letter": letter, "count": len(g["years"]), "n": g["n"], "years": g["years"]})
        row = {s["season"]: s["crop"] for s in e2["seasons"] if s.get("stress_flag")}
        years |= set(row)
        hits.append({"letter": letter, "crops": row})
    years = sorted(years)
    return {"green": green, "years": years,
            "hits": [{"letter": h["letter"], "cells": [h["crops"].get(y) for y in years]} for h in hits]}


def green_line(cross: dict) -> str:
    return " · ".join(f"Field {g['letter']} {g['count']} of {g['n']}" for g in cross["green"])


def headlines(e1: dict, e2: dict, cross: dict, letter: str) -> dict:
    """One message per tab, matching the deck."""
    g = green_after_harvest(e1)["corn"]
    w0, w1 = window_span(e2)
    a = e2["summary"]["all_seasons"]
    more = a["stress_seasons"] > a["expected_stress_seasons"]
    return {
        "cover_title": "Most of the year, no living cover",
        "history_title": "Same rotation on paper, different management on the ground",
        "history": (f"The USDA crop map shows the same corn–soybean rotation on all three fields, but Field {letter} turned green after "
                    f"{len(g['years'])} of its {g['n']} corn harvests. Green after corn harvest: {green_line(cross)}."),
        "evidence_title": "The evidence: every clear satellite pass",
        "conditions_title": "Weather picks the year. Rotation picks the crop.",
        "stress_title": "More often than a typical decade, but not proven" if more else "No more often than a typical decade",
        "options_title": "Three rotations against your priorities",
        "options_intro": ("Stay with corn–soybean, add a cereal rye cover, or add oats with red clover. Each option is rated better, similar or worse "
                          "than the current rotation from this field’s evidence and crop traits; your priorities set the order and never change a rating."),
        "conditions": (f"The same regional years hit all three fields; where each field is in its rotation decides which crop takes the hit. "
                       f"Here, corn silks and soybeans fill pods between {w0} and {w1}, "
                       f"so a corn–soybean rotation always has a crop exposed in those weeks."),
    }


def _rye_months(e3: dict) -> str | None:
    est = e3["ratings"]["cs_rye"]["Soil cover and living roots"].get("estimate") or ""
    m = re.search(r"~([\d.]+) months", est)
    return m.group(1) if m else None


def field_actions(e1: dict, e2: dict, e3: dict, cross: dict) -> list[dict]:
    """Next steps that do not depend on the farmer's priorities."""
    sm, a = e1["summary"], e2["summary"]["all_seasons"]
    rye = e3["ratings"]["cs_rye"]
    by = {r: [k.lower() for k in E3.CRITERIA if rye[k]["rating"] == r] for r in ("better", "similar", "worse")}
    rye_m = _rye_months(e3)
    w0, w1 = window_span(e2)
    g = green_after_harvest(e1)
    gc, gs = g["corn"], g["soybeans"]
    if gc["years"] or gs["years"]:
        parts = [f"{len(x['years'])} of its {x['n']} {crop} harvests" for crop, x in (("corn", gc), ("soybean", gs)) if x["years"]]
        green = (f"This field turned green after {_join(parts)} ({_join(gc['years'] + gs['years'])}). The satellite cannot tell a cover crop "
                 "from volunteers or weeds: if it was a cover, part of the benefit is already there in those years.")
    else:
        green = "This field has not turned green after any harvest since 2016, so the whole off-season is open to a cover crop."
    return [
        {"title": "Cover the gap",
         "text": (f"The soil here goes about {sm['no_living_cover_months_per_year']} months a year without living cover. "
                  + (f"A cereal rye cover after harvest would bring that to about {rye_m} months" if rye_m else "A cereal rye cover after harvest would shorten that")
                  + f": better for {_join(by['better'])}"
                  + (f", similar for {_join(by['similar'])}" if by["similar"] else "")
                  + (f", worse for {_join(by['worse'])}" if by["worse"] else "")
                  + ". That is a lower bound, because rye also grows in spring.")},
        {"title": "Treat weather risk as a calendar problem",
         "text": (f"Both crops reach their sensitive stage between {w0} and {w1}. A dry or hot spell hit {a['stress_seasons']} of "
                  f"{a['seasons']} seasons here ({_join(a['stress_years'])}), against about {a['expected_stress_seasons']} in a typical 1991–2020 decade. "
                  "A crop that is most sensitive outside that window, such as oats in June, lowers exposure in the years it is grown.")},
        {"title": "Check what greens up after harvest",
         "text": f"{green} Green after corn harvest across the three fields: {green_line(cross)}."},
        {"title": "Take this page to your agronomist",
         "text": "Ratings and thresholds are provisional. Start with the checks listed under “Verify with an agronomist”."},
    ]


def priority_action(e3: dict, priorities: list[str], active: set[str]) -> dict:
    """The option your first priority puts on top, and what changes without an oat market. Mirrored in the page's JavaScript."""
    title = "Decide by your first priority"
    if not priorities:
        return {"title": title, "text": "Set your priorities to rank the options."}
    ratings = e3["ratings"]
    kept, _ = E3.apply_constraints(set(active))
    top = E3.rank(ratings, kept, priorities)[0]
    text = f"With {priorities[0].lower()} first, {OPTIONS[top['id']]['phrase']} comes out on top"
    text += ": both alternatives add work that outweighs their gains on that priority." if top["id"] == "cs" else "."
    if "small_grain_market" not in active and top["id"] == "cso_rc":
        kept2, _ = E3.apply_constraints(set(active) | {"small_grain_market"})
        text += f" Without a local market for oats, {OPTIONS[E3.rank(ratings, kept2, priorities)[0]['id']]['phrase']} does instead."
    return {"title": title, "text": text}


def _join_or(xs: list) -> str:
    xs = [str(x) for x in xs]
    return ", ".join(xs[:-1]) + (" or " if len(xs) > 1 else "") + xs[-1] if xs else ""


def stability_line(ratings: dict, kept: list[dict], priorities: list[str]) -> str:
    """One sentence for 'How stable is this?': which option wins whichever priority comes first. Mirrored in the page."""
    if len(kept) == 1:
        return f"Only the {OPTIONS[kept[0]['id']]['label'].lower()} is left after your constraints."
    by_name = {c["name"]: c["id"] for c in E3.CANDIDATES}
    tops = {p: by_name[n] for p, n in E3.what_if(ratings, kept, priorities).items()}
    counts: dict[str, int] = {}
    for i in tops.values():
        counts[i] = counts.get(i, 0) + 1
    most = max(counts, key=lambda i: (counts[i], -list(OPTIONS).index(i)))
    others = [i for i in OPTIONS if i in counts and i != most]
    if not others:
        return f"{OPTIONS[most]['label']} comes out on top whichever priority you put first."
    parts = [f"{_join_or([p.lower() for p, i in tops.items() if i == o])} comes first, when {OPTIONS[o]['phrase']} does" for o in others]
    return f"{OPTIONS[most]['label']} comes out on top unless " + "; or unless ".join(parts) + "."


def actions(e1: dict, e2: dict, e3: dict, cross: dict, priorities: list[str], active: set[str]) -> list[dict]:
    """All next steps in reading order: cover, calendar, priority, green check, agronomist."""
    fa = field_actions(e1, e2, e3, cross)
    return [fa[0], fa[1], priority_action(e3, priorities, active), fa[2], fa[3]]


def trend_message(trends: list[dict], stress_seasons: int, seasons: int) -> dict:
    """Headline for the mid-summer trends. trends: dicts with title, unit, slope (per decade) and p."""
    sig = [x for x in trends if x["p"] < SIGNIFICANT_P]
    heat = next((x for x in trends if x["title"].startswith("Daily maximum")), None)
    hot = next((x for x in trends if x["title"].startswith("Days above")), None)
    if sig:
        title = "Is it changing? Yes: " + _join([x["title"].split(",")[0].lower() for x in sig])
    else:
        title = "Is it changing? Not clearly, yet"
    lead = (f"Mid-summer highs are edging up ({heat['slope']:+.1f} °C and {hot['slope']:+.1f} days above 30 °C per decade since 1981), "
            if heat and hot and heat["slope"] > 0 else "")
    if sig:
        text = lead + f"and the change in {_join([x['title'].split(',')[0].lower() for x in sig])} is statistically significant (p < {SIGNIFICANT_P})."
    else:
        pmin = min(x["p"] for x in trends)
        text = (lead + ("but " if lead else "") + f"year-to-year swings are larger: no mid-summer trend here is statistically significant (p ≥ {pmin:.2f}). "
                f"The risk to plan for is the swings you already see: {stress_seasons} of {seasons} seasons hit at the sensitive stage.")
    return {"title": title, "text": text}


def validation_summary() -> list[str]:
    """One line per check, read from the validation files the notebook writes (see docs/validation_results.md)."""
    import pandas as pd

    lines = []
    def csv(name):
        p = PROCESSED / name
        return pd.read_csv(p) if p.exists() else None
    v3, v4, v6, v13 = csv("v3_mslsp_greenup.csv"), csv("v4_silking_check.csv"), csv("v6_visual_calls.csv"), csv("v13_usdm_windows.csv")
    v11 = pd.read_csv(PROCESSED / "v11_smap_power.csv", index_col=0) if (PROCESSED / "v11_smap_power.csv").exists() else None
    if v3 is not None:
        lines.append(f"Green-up dates match NASA’s own MSLSP30NA phenology within 10 days in {int((v3.diff_days.abs() <= 10).sum())} of {len(v3)} field-seasons (2016–2019).")
    if v4 is not None:
        miss = v4[~v4.inside]
        where = sorted({str(f)[-1].upper() for f in miss.field})
        tail = (f"; all {len(miss)} misses are on Field {where[0]} ({_join(sorted(miss.season))})" if len(where) == 1
                else f"; misses on Fields {_join(where)}" if where else "")
        lines.append(f"Estimated corn silking falls inside Iowa’s 25–75% silked dates (USDA Crop Progress) in {int(v4.inside.sum())} of {len(v4)} corn seasons{tail}.")
    if v6 is not None:
        rnd = v6[v6.set.str.startswith("random")]
        lines.append(f"Off-season cover calls match true-colour satellite images on {int(rnd.match.sum())} of {len(rnd)} random dates (rated blind by AI; to be spot-checked).")
    if v11 is not None:
        lines.append(f"NASA SMAP soil moisture agrees with the dry calls in {min(int(s.split('/')[0]) for s in v11.flags_agree)}–{max(int(s.split('/')[0]) for s in v11.flags_agree)} of 10 seasons per field.")
    if v13 is not None:
        dry = v13[v13.power_dry]
        missed = v13[v13.dry_d1 & ~v13.power_dry]
        by_year: dict[int, list[str]] = {}
        for r in missed.itertuples():
            by_year.setdefault(int(r.season), []).append(str(r.field)[-1].upper())
        gaps = "; ".join(f"{y} on Field{'s' if len(f) > 1 else ''} {_join(sorted(f))}" for y, f in sorted(by_year.items(), key=lambda kv: (-len(kv[1]), kv[0])))
        lines.append(f"U.S. Drought Monitor: {int(dry.dry_d0.sum())} of {len(dry)} dry calls fall in at least abnormally dry weeks, {int(dry.dry_d1.sum())} in moderate drought"
                     + (f"; drought the tool missed: {gaps}." if gaps else "."))
    import json
    diffs = []
    for f in ("field_a", "field_b", "field_c"):
        p = PROCESSED / f / "field_static.json"
        if p.exists():
            tr = json.loads(p.read_text())["terrain"]
            diffs.append(abs(tr["mean_slope_pct"]["value"] - tr["ref_3dep_10m_pct"]["value"]))
    if diffs:
        lines.append(f"Field slope from NASADEM, once smoothed, is within {max(diffs):.2f} percentage points of USGS lidar on every field.")
    return lines


# ---------------------------------------------------------------- what worked, field by field
GREEN_YEAR_DAYS = E3.GREEN_YEAR_DAYS  # a cover year with >= 30 off-season living days counts as "with green" (as Engine 3)
USDM_WORDS = {"D0": "abnormally dry", "D1": "moderate drought", "D2": "severe drought", "D3": "extreme drought", "D4": "exceptional drought"}
VIGOUR_CAVEAT = ("Vigour is the season’s peak and total greenness against this field’s own normal for the crop, not yield, and peak greenness "
                 "saturates near 0.9, so “held” can overstate resilience. Green after harvest is not confirmed as a cover crop. "
                 "Ten seasons per field: patterns to discuss, not proof.")


def _median(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    return (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2) if n else float("nan")


def field_worked(letter: str, e1: dict, e2: dict) -> dict:
    """What the record says worked on one field: cover years, stress resilience, weaker seasons and their likely reasons."""
    s2 = {s["season"]: s for s in e2["seasons"]}
    # soil cover: complete cover years with off-season green vs without, within the same crop (Engine 3's rule)
    cover = None
    by_crop: dict[str, dict[str, list]] = {}
    for s in e1["seasons"]:
        if s.get("cover_year_partial") or s.get("no_living_cover_share") is None or s.get("off_season_living_days") is None:
            continue
        kind = "with" if s["off_season_living_days"] >= GREEN_YEAR_DAYS else "without" if s["off_season_living_days"] <= 5 else None
        if kind:
            by_crop.setdefault(s["crop"], {"with": [], "without": []})[kind].append(s)
    for crop, d in by_crop.items():
        if d["with"] and d["without"]:
            w = round(_median([x["no_living_cover_share"] for x in d["with"]]) * 12, 1)
            wo = round(_median([x["no_living_cover_share"] for x in d["without"]]) * 12, 1)
            after = [s2[x["season"]]["vigour"] for x in d["with"] if x["season"] in s2]
            cover = {"crop": crop, "with_years": [x["season"] for x in d["with"]], "with_months": w, "without_months": wo,
                     "n_without": len(d["without"]), "diff": round(wo - w, 1), "vigour_after": after}
    months = [round(s["no_living_cover_share"] * 12, 1) for s in e1["seasons"] if s.get("no_living_cover_share") is not None and not s.get("cover_year_partial")]
    flagged = [s for s in e2["seasons"] if s.get("stress_flag")]
    held = [s["season"] for s in flagged if s["vigour"] in ("similar", "above")]
    dropped = [(s["season"], s["crop"]) for s in flagged if s["vigour"] == "below"]
    dips = []
    for s in e2["seasons"]:
        if s.get("stress_flag") or s["vigour"] != "below":
            continue
        why = []
        if s.get("esi_status") == "low":
            why.append("ECOSTRESS showed stress at field scale")
        if s.get("usdm_category") in USDM_WORDS:
            why.append(f"Drought Monitor: {USDM_WORDS[s['usdm_category']]} in the window")
        dips.append({"season": s["season"], "crop": s["crop"], "why": why})
    lines = []
    if cover:
        crop_word = "soybean" if cover["crop"] == "soybeans" else cover["crop"]
        one = len(cover["with_years"]) == 1
        lines.append(f"Green after harvest went with less bare soil: in the {crop_word} year{'' if one else 's'} that followed it ({_join(cover['with_years'])}), "
                     f"{cover['with_months']} months went without living cover, against {cover['without_months']} in this field’s other {crop_word} "
                     f"year{'s' if cover['n_without'] > 1 else ''}: about {cover['diff']} months less."
                     + (f" The {crop_word}{' crop' if one else 's'} that followed showed no drop in vigour." if cover["vigour_after"] and all(v in ("similar", "above") for v in cover["vigour_after"]) else ""))
    else:
        lines.append(f"No green after harvest, so no cover years to learn from: the soil went without living cover {min(months)}–{max(months)} months every year.")
    if flagged:
        lines.append(f"Crops held their vigour in {len(held)} of {len(flagged)} seasons hit by a dry or hot spell"
                     + (f"; the exception: {_join([f'{c} in {y}' for y, c in dropped])}." if dropped else "."))
    if dips:
        lines.append("Weaker seasons the regional weather did not flag: "
                     + "; ".join(f"{d['season']} {d['crop']} ({', '.join(d['why']) if d['why'] else 'no cause in the data; ask the farmer'})" for d in dips) + ".")
    else:
        lines.append("No weaker seasons outside the flagged years.")
    return {"letter": letter, "cover": cover, "flagged": len(flagged), "held": len(held), "dropped": dropped, "dips": dips, "lines": lines,
            "uncovered_range": [min(months), max(months)] if months else None}


def what_worked(fields: list[tuple[str, dict, dict]]) -> dict:
    """The cross-field view for the 'What worked' section."""
    per = [field_worked(L, e1, e2) for L, e1, e2 in fields]
    held, flagged = sum(p["held"] for p in per), sum(p["flagged"] for p in per)
    green = [p for p in per if p["cover"]]
    best = max(green, key=lambda p: p["cover"]["diff"]) if green else None
    dips = [f"{p['letter']} {d['season']}" for p in per for d in p["dips"]]
    explained = all(d["why"] for p in per for d in p["dips"])
    lead = f"Across the three fields, crops held their vigour in {held} of {flagged} seasons hit by a dry or hot spell."
    if best:
        lead += (f" Field {best['letter']}, which most often turned green after harvest, had about {best['cover']['diff']} months less bare soil "
                 "in the years that followed, with no sign of a vigour penalty." if all(v in ("similar", "above") for v in best["cover"]["vigour_after"])
                 else f" Field {best['letter']}, which most often turned green after harvest, had about {best['cover']['diff']} months less bare soil in the years that followed.")
    if dips:
        lead += (f" The weaker seasons the regional flags missed ({_join(dips)}) line up with field-scale ECOSTRESS stress or the Drought Monitor, "
                 "which is why the field-scale checks matter." if explained else f" Weaker seasons the regional flags missed: {_join(dips)}.")
    return {"title": "What worked, field by field", "lead": lead, "fields": per, "caveat": VIGOUR_CAVEAT}
