"""The deck's messages and the farmer's next steps, built only from the evidence JSON (V8).

Shared by the Streamlit app and the standalone page (app/build_web.py embeds the static
parts; the page mirrors `priority_action` in JavaScript, checked by tests/test_web_parity.py).
"""

from __future__ import annotations

import re
from datetime import date

from pipeline import engine3 as E3

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
    return {
        "history": (f"Same rotation on paper as its neighbours, different management on the ground. Field {letter} turned green after "
                    f"{len(g['years'])} of its {g['n']} corn harvests (green after corn harvest: {green_line(cross)})."),
        "conditions_title": "Weather picks the year. Rotation picks the crop.",
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
    text = f"With {priorities[0].lower()} first, {top['name']} ranks first."
    if top["id"] == "cs":
        text += " Both alternatives add work that outweighs their gains on that priority."
    if "small_grain_market" not in active and top["id"] == "cso_rc":
        kept2, _ = E3.apply_constraints(set(active) | {"small_grain_market"})
        text += f" Without a local market for oats, {E3.rank(ratings, kept2, priorities)[0]['name']} ranks first instead."
    text += " Changing priorities reorders the options; it never changes a rating."
    return {"title": title, "text": text}


def actions(e1: dict, e2: dict, e3: dict, cross: dict, priorities: list[str], active: set[str]) -> list[dict]:
    """All next steps in reading order: cover, calendar, priority, green check, agronomist."""
    fa = field_actions(e1, e2, e3, cross)
    return [fa[0], fa[1], priority_action(e3, priorities, active), fa[2], fa[3]]
