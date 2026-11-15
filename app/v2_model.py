"""Field Shift V2: a guided rotation plan for the farmer, built from the same evidence as V1.

What V2 changes, from what V1 taught us:
- The farmer's answers feed the analysis: whether green after harvest was a planted cover,
  weeds or not sure changes the local cover effect and every estimate built on it.
- A farm view (three fields) with where to start, not one field at a time.
- The season calendar: each option's living cover and sensitive stages, against this farm's
  measured heat and root-zone wetness through the summer. The water rating compares measured
  exposure instead of "at least one flagged season".
- A plan: the farmer's own choice, a small start on the best field, a season checklist,
  questions for the agronomist, and what Field Shift checks next season.

Everything is computed from data/processed (V8 traceability). The page recomputes the cover
effect, estimates, ranking and where-to-start live in JavaScript; tests/test_v2.py checks
the JavaScript against these functions.
"""

from __future__ import annotations

import statistics
from datetime import date, timedelta

import pandas as pd

from app import data as D
from app import takeaways as T
from pipeline import engine3 as E3
from pipeline.crop_catalogue import CATALOGUE

YEARS = (2016, 2025)
HOT_C = 30.0
OATS_WINDOW = ("06-01", "06-30")  # heading to grain fill, "typically June" (crop catalogue: PFI, ISU)
MEANINGFUL_MONTHS = E3.MEANINGFUL_MONTHS
WET_DIFF, HOT_DIFF = 0.03, 0.03  # smallest differences in wetness (0-1) or hot-day share counted as a real difference
ROTATIONS = {"cs": ["corn", "soybeans"], "cs_rye": ["corn", "soybeans"], "cso_rc": ["corn", "soybeans", "oats"]}
HALVES = [(m, h) for m in range(5, 10) for h in (1, 2)]  # May to September, two halves a month


def _md_doy(md: str) -> int:
    return date.fromisoformat(f"2001-{md}").timetuple().tm_yday


def _doy_md(doy: float) -> str:
    return (date(2001, 1, 1) + timedelta(days=round(doy) - 1)).strftime("%m-%d")


def _label(md: str) -> str:
    d = date.fromisoformat(f"2001-{md}")
    return f"{d.day} {d:%b}"


# ---------------------------------------------------------------- season climate and exposure
def _years(power: pd.DataFrame) -> pd.DataFrame:
    return power[(power.index.year >= YEARS[0]) & (power.index.year <= YEARS[1])]


def season_climate(power: pd.DataFrame) -> list[dict]:
    """Half-month heat and root-zone wetness, May to September, over the last ten seasons."""
    p = _years(power)
    out = []
    for m, h in HALVES:
        sel = p[(p.index.month == m) & ((p.index.day <= 15) if h == 1 else (p.index.day > 15))]
        start = f"{m:02d}-{'01' if h == 1 else '16'}"
        end = f"{m:02d}-15" if h == 1 else (date(2001, m % 12 + 1, 1) - timedelta(days=1)).strftime("%m-%d")
        out.append({"start": start, "end": end, "label": f"{_label(start)}–{_label(end)}",
                    "hot_share": round(float((sel["T2M_MAX"] > HOT_C).mean()), 3),
                    "wetness": round(float(sel["GWETROOT"].mean()), 3),
                    "rain_mm_day": round(float(sel["PRECTOTCORR"].mean()), 2)})
    return out


def median_windows(e2: dict) -> dict[str, tuple[str, str]]:
    """This field's typical sensitive window per crop (median start and end day), plus oats from the catalogue."""
    out = {}
    for crop in ("corn", "soybeans"):
        ws = [s for s in e2["seasons"] if s.get("crop") == crop and s.get("window_start")]
        if ws:
            out[crop] = (_doy_md(statistics.median(_md_doy(s["window_start"][5:]) for s in ws)),
                         _doy_md(statistics.median(_md_doy(s["window_end"][5:]) for s in ws)))
    out["oats"] = OATS_WINDOW
    return out


def window_climate(power: pd.DataFrame, start: str, end: str) -> dict:
    p = _years(power)
    doy = p.index.dayofyear - ((p.index.year % 4 == 0) & (p.index.month > 2)).astype(int)  # non-leap calendar days
    sel = p[(doy >= _md_doy(start)) & (doy <= _md_doy(end))]
    return {"hot_share": round(float((sel["T2M_MAX"] > HOT_C).mean()), 3), "wetness": round(float(sel["GWETROOT"].mean()), 3)}


def exposure(power: pd.DataFrame, windows: dict) -> dict:
    """Heat and wetness in each crop's sensitive window, averaged over each option's rotation years."""
    clim = season_climate(power)
    hottest = max(clim, key=lambda c: c["hot_share"])
    crops = {}
    for crop, (s, e) in windows.items():
        w = window_climate(power, s, e)
        w["overlaps_hottest"] = _md_doy(s) <= _md_doy(hottest["end"]) and _md_doy(e) >= _md_doy(hottest["start"])
        crops[crop] = {**w, "start": s, "end": e, "label": f"{_label(s)}–{_label(e)}"}
    options = {}
    for oid, rot in ROTATIONS.items():
        options[oid] = {"hot_share": round(statistics.mean(crops[c]["hot_share"] for c in rot), 3),
                        "wetness": round(statistics.mean(crops[c]["wetness"] for c in rot), 3),
                        "years_in_hottest": sum(crops[c]["overlaps_hottest"] for c in rot), "rotation_years": len(rot)}
    return {"hottest": hottest, "crops": crops, "options": options}


# ---------------------------------------------------------------- cover effect with the farmer's answers
def cover_rows(fields: dict[str, dict]) -> list[dict]:
    """Complete-or-partial cover years from every field, the inputs to the cover effect. fields: letter -> engine1 doc."""
    rows = []
    for letter, e1 in fields.items():
        for s in e1["seasons"]:
            rows.append({"field": letter, "season": s["season"], "crop": s["crop"], "share": s.get("no_living_cover_share"),
                         "off": s.get("off_season_living_days"), "partial": bool(s.get("cover_year_partial"))})
    return rows


def cover_effect(rows: list[dict], exclude: frozenset = frozenset()) -> dict | None:
    """Engine 3's local cover effect (median within-crop gap between cover years with and without off-season green),
    leaving out cover years the farmer says were weeds or volunteers. exclude: {(letter, cover_year)}."""
    by_crop: dict[str, dict[str, list]] = {}
    for r in rows:
        if r["partial"] or r["share"] is None or r["off"] is None:
            continue
        kind = "with" if r["off"] >= E3.GREEN_YEAR_DAYS else "without" if r["off"] <= 5 else None
        if kind == "with" and (r["field"], r["season"]) in exclude:
            continue
        if kind:
            by_crop.setdefault(r["crop"], {"with": [], "without": []})[kind].append(r)
    diffs, used = [], []
    for d in by_crop.values():
        if d["with"] and d["without"]:
            diffs.append(statistics.median(x["share"] for x in d["without"]) - statistics.median(x["share"] for x in d["with"]))
            used += [(x["field"], x["season"]) for x in d["with"]]
    if not diffs:
        return None
    eff = statistics.median(diffs)
    return {"share_reduction": round(eff, 3), "months_per_year": round(eff * 12, 1), "cover_years": sorted(used)}


def estimate_months(rows: list[dict], letter: str, effect: dict | None) -> float | None:
    """Months a year without living cover if every uncovered cover year gained the local effect (Engine 3's rule)."""
    if not effect:
        return None
    shares = []
    for r in rows:
        if r["field"] != letter or r["partial"] or r["share"] is None:
            continue
        sh = r["share"]
        if (r["off"] or 0) < E3.GREEN_YEAR_DAYS:
            sh = max(0.0, sh - effect["share_reduction"])
        shares.append(sh)
    return round(statistics.mean(shares) * 12, 1) if shares else None


def rye_soil_rating(cur: float, est: float | None, effect: dict | None) -> str:
    """Engine 3's soil-cover rule for the rye option: better if the measured gain is at least half a month; better by
    crop traits alone when there is no local evidence. Mirrored in the page (ryeSoilRating)."""
    return ("better" if cur - est >= MEANINGFUL_MONTHS else "similar") if effect and est is not None else "better"


def current_months(rows: list[dict], letter: str) -> float:
    shares = [r["share"] for r in rows if r["field"] == letter and not r["partial"] and r["share"] is not None]
    return round(statistics.mean(shares) * 12, 1)


def green_autumns(letter: str, e1: dict) -> list[dict]:
    """Autumns with green after harvest, to ask the farmer about. The cover year it feeds is the next season."""
    seasons = {s["season"] for s in e1["seasons"]}
    return [{"field": letter, "autumn": s["season"], "after": s["crop"], "cover_year": s["season"] + 1 if s["season"] + 1 in seasons else None}
            for s in e1["seasons"] if (s.get("autumn_green_obs") or 0) >= T.GREEN_MIN_OBS]


def where_to_start(option: str, farm: list[dict], gains: dict[str, float | None]) -> dict | None:
    """The field to try an option on first. Rye: the largest measured gain, started after a corn harvest so the rye
    precedes soybeans (avoids nitrogen tie-up ahead of corn, ISU). Oats + clover: oats follow soybeans, so a field
    in soybeans in 2026 (if the alternation continued), the one with most bare months."""
    if option == "cs_rye":
        cand = [f for f in farm if gains.get(f["letter"]) is not None]
        if not cand:
            return None
        f = max(cand, key=lambda x: (gains[x["letter"]], -ord(x["letter"])))
        return {"field": f["letter"], "start_year": start_year(option, f), "why": f"the largest gain in living cover ({gains[f['letter']]:.1f} months a year)"}
    if option == "cso_rc":
        cand = [f for f in farm if f["crop_2026"] == "soybeans"]
        if not cand:
            return None
        f = max(cand, key=lambda x: (x["bare_months"], -ord(x["letter"])))
        return {"field": f["letter"], "start_year": start_year(option, f), "why": f"in soybeans in 2026 and the most bare months ({f['bare_months']:.1f} a year)"}
    return None


# ---------------------------------------------------------------- is it changing? and the soil
def _signed(x: float, fmt: str) -> str:
    return format(x, "+" + fmt).replace("-", "\u2212")


def trend_summary(power: pd.DataFrame, stress: int, seasons: int) -> dict:
    """Is mid-summer changing here? V1's least-squares trends (15 Jun-15 Aug, since 1981) with two-sided p-values."""
    m = D.window_metrics(power)
    t = {col: {"title": D.METRICS[col][0], "slope": round(D.trend_per_decade(m, col), 3), "p": round(D.trend_pvalue(m, col), 3)}
         for col in D.METRICS}
    sig = [col for col, v in t.items() if v["p"] < T.SIGNIFICANT_P]
    since = int(m.index.min())
    change = (f"Since {since}, mid-June to mid-August highs moved {_signed(t['tmax_c']['slope'], '.1f')} °C and "
              f"{_signed(t['hot_days']['slope'], '.1f')} days above 30 °C per decade, rainfall {_signed(t['rain_mm']['slope'], '.0f')} mm and "
              f"root-zone wetness {_signed(t['gwetroot']['slope'], '.2f')} per decade.")
    if sig:
        names = ", ".join(t[c]["title"].split(",")[0].lower() for c in sig)
        verdict = f" The change in {names} is statistically significant (p < {T.SIGNIFICANT_P}): plan for it as a trend."
    else:
        pmin = min(v["p"] for v in t.values())
        verdict = (f" None of these trends is statistically significant (p \u2265 {pmin:.2f}): the swings from year to year are larger than the change. "
                   f"Plan for the swings, which hit the crop at its sensitive stage in {stress} of {seasons} recent seasons.")
    return {"since": since, "metrics": t, "significant": bool(sig),
            "title": "Is it changing? " + ("Yes" if sig else "Not clearly, yet"), "text": change + verdict}


def soil_note(farm: list[dict]) -> str:
    """What the local soil says across the farm (USDA SSURGO, area-weighted over each field's map units)."""
    aws = [f["aws"] for f in farm]
    drains = sorted({f["drainage"] for f in farm})
    same = max(aws) - min(aws) < 1.0
    water = (f"The soil holds about the same water on all three fields: {min(aws):.1f}\u2013{max(aws):.1f} cm in the top metre "
             if same else f"The soil holds {min(aws):.1f}\u2013{max(aws):.1f} cm of water in the top metre ")
    return (water + "(USDA SSURGO). It buffers short dry spells alike on every field, so soil does not change which option suits which field; "
            "the satellite record does. " + ("Drainage differs: " + ", ".join(f"Field {f['letter']} {f['drainage'].lower()}" for f in farm) + "."
                                             if len(drains) > 1 else f"All three are {drains[0].lower()}."))


# ---------------------------------------------------------------- ratings (V1's, with the revised water and erosion rules)
def ratings_v2(e3: dict, expo: dict, static: dict) -> dict:
    r = {cid: {k: dict(v) for k, v in crit.items()} for cid, crit in e3["ratings"].items()}
    cs, oats = expo["options"]["cs"], expo["crops"]["oats"]
    wet_gain, hot_gain = oats["wetness"] - cs["wetness"], cs["hot_share"] - oats["hot_share"]
    better = wet_gain >= WET_DIFF or hot_gain >= HOT_DIFF
    r["cso_rc"]["Water and stress exposure"] = E3.cell(
        "better" if better else "similar",
        (f"Measured on this farm, 2016–2025: in the oats year the sensitive stage moves to June, when root-zone wetness averages "
         f"{oats['wetness']:.2f} against {cs['wetness']:.2f} in the corn and soybean windows, and {oats['hot_share']:.0%} of days pass 30 °C "
         f"against {cs['hot_share']:.0%}. Corn and soybeans are exposed in 2 years of 3 instead of every year."),
        "moderate", "Oat heading dates locally; clover's late-summer water use.")
    r["cs_rye"]["Water and stress exposure"] = E3.cell(
        "similar",
        (f"Same cash crops and the same windows: {cs['hot_share']:.0%} of days above 30 °C and wetness {cs['wetness']:.2f} on average. "
         f"Rye {CATALOGUE['cereal rye']['water']}."),
        "moderate", "Earlier rye termination in a dry spring.")
    aws = static["soil"]["aws0100wta"]["value"]
    for cid in ("cs_rye", "cso_rc"):
        r[cid]["Water and stress exposure"]["evidence"] += (
            f" Soil: about {aws:.1f} cm of water held in the top metre (USDA SSURGO), which buffers short dry spells "
            "alike under every option.")
    terr = static["terrain"]
    small = terr["mean_slope_pct"]["value"] < 3 and terr["p90_slope_pct"]["value"] < 3.5
    for cid in ("cs_rye", "cso_rc"):
        c = r[cid]["Erosion protection"]
        if small:
            c["evidence"] += f" On this field the benefit is small: mean slope {terr['mean_slope_pct']['value']}%, flat ground."
    return r


# ---------------------------------------------------------------- the plan
def plan_steps(option: str, start: dict | None) -> list[dict]:
    """Season checklist for the chosen option on the start field (catalogue guidance; confirm locally)."""
    if option == "cs_rye" and start:
        f, y = start["field"], start["start_year"]
        return [
            {"when": "This winter", "what": f"Talk to your agronomist and seed supplier: rye seed, how you will sow it on Field {f}, and how and when you will end it in spring. Check any insurance or programme rules on ending cover crops."},
            {"when": f"After the {y} corn harvest", "what": f"Sow cereal rye on Field {f} as soon as practical. Starting ahead of soybeans avoids the main risk of rye before corn: nitrogen tie-up if it is ended late (ISU)."},
            {"when": f"Spring {y + 1}", "what": f"End the rye before planting soybeans on Field {f}, and note the date and method."},
            {"when": f"{y + 1} season", "what": "Compare: Field Shift will show spring green, months without living cover and soybean vigour against the field’s own history."},
        ]
    if option == "cso_rc" and start:
        f, y = start["field"], start["start_year"]
        return [
            {"when": "This winter", "what": "Line up a buyer or on-farm use for oats and straw, seed for oats and red clover, and small-grain harvest (own, borrowed or custom)."},
            {"when": f"Spring {y}", "what": f"Plant oats on Field {f} instead of corn, with red clover sown with them or frost-seeded (PFI)."},
            {"when": f"July {y}", "what": "Harvest the oats; the clover keeps the soil covered through autumn and winter."},
            {"when": f"Spring {y + 1}", "what": f"End the clover ahead of corn on Field {f}; ask your agronomist how much nitrogen credit to count (PFI, SARE)."},
        ]
    return [
        {"when": "This season", "what": "No change to operations."},
        {"when": "Worth doing anyway", "what": "Confirm what greened up after harvest (step 2), and scout in the late-July weeks when this farm’s hottest days fall."},
    ]


def monitoring(option: str, start: dict | None) -> list[str]:
    f = f"Field {start['field']}" if start else "each field"
    common = ["Dry or hot spells at each crop’s sensitive stage, against the 1991–2020 base rate."]
    if option == "cs_rye":
        return [f"Spring green on {f} in March and April (the rye’s spring growth).", f"Months without living cover on {f} for the cover year, against its own history.", *common]
    if option == "cso_rc":
        return [f"Living cover on {f} from the oat harvest through the next spring.", f"Corn vigour on {f} the year after the clover, against its own history.", *common]
    return ["Months without living cover on every field, each cover year.", *common]


def start_year(option: str, f: dict) -> int:
    """First season of the option on field f, if the corn–soybean alternation continued in 2026."""
    if option == "cs_rye":
        return 2027 if f["corn_parity"] == 1 else 2028  # sown after a corn harvest, ahead of soybeans
    return 2027 if f["crop_2026"] == "soybeans" else 2028  # oats follow soybeans


def plans_by_field(farm: list[dict]) -> dict:
    """The plan for every option on every possible start field, so the page can follow the farmer's answers."""
    out = {"cs": {"_": {"steps": plan_steps("cs", None), "checks": monitoring("cs", None)}}}
    for o in ("cs_rye", "cso_rc"):
        out[o] = {}
        for f in farm:
            s = {"field": f["letter"], "start_year": start_year(o, f)}
            out[o][f["letter"]] = {"steps": plan_steps(o, s), "checks": monitoring(o, s), "start_year": s["start_year"]}
    return out


# ---------------------------------------------------------------- everything the page needs
def build() -> dict:
    fids = D.field_ids()
    letters = {f: f.split("_")[-1].upper() for f in fids}
    docs = {f: (D.load_engine1(f), D.load_engine2(f), D.load_engine3(f), D.load_static(f)) for f in fids}
    rows = cover_rows({letters[f]: docs[f][0] for f in fids})
    effect = cover_effect(rows)
    worked = T.what_worked([(letters[f], docs[f][0], docs[f][1]) for f in fids])
    v4 = pd.read_csv(D.PROCESSED / "v4_silking_check.csv") if (D.PROCESSED / "v4_silking_check.csv").exists() else None
    farm, fields = [], {}
    for f in fids:
        e1, e2, e3, st = docs[f]
        L = letters[f]
        power = D.load_power(f)
        wins = median_windows(e2)
        expo = exposure(power, wins)
        corn_years = [s["season"] for s in e1["seasons"] if s["crop"] == "corn"]
        parity = corn_years[0] % 2 if corn_years else 0
        cur = current_months(rows, L)
        a = e2["summary"]["all_seasons"]
        wk = next(p for p in worked["fields"] if p["letter"] == L)
        late = ([{"season": int(r.season), "days_from_50": int(r.days_from_50)} for r in v4[(v4.field.astype(str).str[-1].str.upper() == L) & ~v4.inside].itertuples()]
                if v4 is not None else [])
        farm.append({"letter": L, "area": st["area_ha"]["value"], "drainage": st["soil"]["drclassdcd"]["value"], "slope": st["terrain"]["mean_slope_pct"]["value"],
                     "aws": round(st["soil"]["aws0100wta"]["value"], 1),
                     "bare_months": cur, "corn_parity": parity, "crop_2026": "corn" if parity == 0 else "soybeans",
                     "green": green_autumns(L, e1), "green_corn": [g["autumn"] for g in green_autumns(L, e1) if g["after"] == "corn"],
                     "corn_harvests": len(corn_years), "stress": a["stress_seasons"], "seasons": a["seasons"], "expected": a["expected_stress_seasons"],
                     "held": wk["held"], "flagged": wk["flagged"], "worked": wk["lines"], "late_silking": late})
        fields[L] = {"id": f, "county": D.demo_props().get(f, {}).get("county", ""), "climate": season_climate(power), "windows": wins,
                     "exposure": expo, "ratings": ratings_v2(e3, expo, st), "notes": e3["notes"], "not_established": e3["not_established"],
                     "sources": e3["sources"], "living_cover": (sp := {crop: _living_span(e1, crop) for crop in ("corn", "soybeans")}),
                     "calendar": calendar_rows(sp, wins), "trend": trend_summary(power, a["stress_seasons"], a["seasons"])}
    gains = {f["letter"]: (round(f["bare_months"] - est_, 1) if (est_ := estimate_months(rows, f["letter"], effect)) is not None else None) for f in farm}
    return {
        "title": "Field Shift V2",
        "decision": T.DECISION,
        "farm": farm, "soil_note": soil_note(farm), "fields": fields, "cover_rows": rows, "effect": effect, "gains": gains,
        "start": {o: where_to_start(o, farm, gains) for o in ("cs_rye", "cso_rc")},
        "options": T.OPTIONS, "rotations": ROTATIONS, "oats_window": OATS_WINDOW,
        "catalogue": {k: {kk: vv for kk, vv in v.items() if kk != "sources"} for k, v in CATALOGUE.items()},
        "engine3": {"PRIORITIES": E3.PRIORITIES, "CRITERIA": E3.CRITERIA, "CRITERIA_FOR_PRIORITY": E3.CRITERIA_FOR_PRIORITY,
                    "CANDIDATES": [{"id": c["id"], "name": c["name"], "needs": sorted(c["needs"])} for c in E3.CANDIDATES],
                    "CONSTRAINTS": E3.CONSTRAINTS, "OPTIONS": T.OPTIONS, "GREEN_YEAR_DAYS": E3.GREEN_YEAR_DAYS, "MEANINGFUL_MONTHS": MEANINGFUL_MONTHS},
        "plans": plans_by_field(farm),
        "worked_lead": worked["lead"], "caveat": worked["caveat"], "validation": T.validation_summary(),
    }


TERMINATE_BEFORE_GREENUP = 45  # days: planned end of a cover ahead of the crop's 50% green-up (about 2 weeks before planting)
HARVEST_AFTER_SENESCENCE = 21  # days: planned sowing of a cover after the canopy dies back (harvest)
OATS_SPAN = ("04-01", "07-15")  # planted early spring, harvested in July (crop catalogue: PFI)


def calendar_rows(spans: dict, windows: dict) -> dict:
    """Each option's year-by-year calendar (day of year 1-365): observed crop canopy, planned cover, bare soil,
    and the crop's sensitive window. Planned cover timings are illustrative, from the crop catalogue."""
    def crop_year(crop, cover_before=None, cover_after=None):
        g, e = _md_doy(spans[crop]["start"]), _md_doy(spans[crop]["end"])
        seg, t = [], 1
        if cover_before:
            end = g - TERMINATE_BEFORE_GREENUP
            seg.append({"kind": "cover", "name": cover_before, "start": 1, "end": end})
            t = end + 1
        seg.append({"kind": "bare", "start": t, "end": g - 1})
        seg.append({"kind": "crop", "name": crop, "start": g, "end": e})
        if cover_after:
            s = e + HARVEST_AFTER_SENESCENCE
            seg += [{"kind": "bare", "start": e + 1, "end": s - 1}, {"kind": "cover", "name": cover_after, "start": s, "end": 365}]
        else:
            seg.append({"kind": "bare", "start": e + 1, "end": 365})
        return {"crop": crop, "segments": seg, "window": {"start": _md_doy(windows[crop][0]), "end": _md_doy(windows[crop][1])}}
    o0, o1 = _md_doy(OATS_SPAN[0]), _md_doy(OATS_SPAN[1])
    oats = {"crop": "oats", "segments": [{"kind": "bare", "start": 1, "end": o0 - 1}, {"kind": "crop", "name": "oats", "start": o0, "end": o1},
                                         {"kind": "cover", "name": "red clover", "start": o1 + 1, "end": 365}],
            "window": {"start": _md_doy(windows["oats"][0]), "end": _md_doy(windows["oats"][1])}}
    return {
        "cs": [crop_year("corn"), crop_year("soybeans")],
        "cs_rye": [crop_year("corn", "cereal rye", "cereal rye"), crop_year("soybeans", "cereal rye", "cereal rye")],
        "cso_rc": [crop_year("corn", cover_before="red clover"), crop_year("soybeans"), oats],
    }


def _living_span(e1: dict, crop: str) -> dict | None:
    """Typical living-canopy span for a crop on this field: median green-up to median end of living cover."""
    ss = [s for s in e1["seasons"] if s["crop"] == crop and s.get("greenup_date") and s.get("living_cover_end")]
    if not ss:
        return None
    return {"start": _doy_md(statistics.median(_md_doy(s["greenup_date"][5:]) for s in ss)),
            "end": _doy_md(statistics.median(_md_doy(s["living_cover_end"][5:]) for s in ss))}
