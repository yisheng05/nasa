"""Engine 3: Rotation Comparison (handoff §8.3).

Transparent rules, no optimiser. Each candidate rotation gets an ordinal rating
(better / similar / worse) *relative to the current rotation* on each criterion, with
the evidence behind it, a confidence and what to verify. Ratings depend only on the
field's evidence and the crop catalogue; the farmer's priorities and constraints are
applied afterwards (filter, then sort), so changing priorities can reorder candidates
but never changes a rating (V9).

Income is not predicted (handoff §3.4).
"""

from __future__ import annotations

import statistics

from .crop_catalogue import CATALOGUE, SOURCE_NAMES

PRIORITIES = [
    "Soil protection",
    "Water and stress risk",
    "Nitrogen and input needs",
    "Workload and simplicity",
    "Crop diversity",
]
CRITERIA_FOR_PRIORITY = {
    "Soil protection": ["Soil cover and living roots", "Erosion protection"],
    "Water and stress risk": ["Water and stress exposure"],
    "Nitrogen and input needs": ["Nitrogen needs"],
    "Workload and simplicity": ["Workload and complexity"],
    "Crop diversity": ["Crop diversity"],
}
CRITERIA = [c for p in PRIORITIES for c in CRITERIA_FOR_PRIORITY[p]]

CANDIDATES = [
    {"id": "cs", "name": "Corn–soybean (current)", "crops": ["corn", "soybeans"], "covers": [], "needs": set()},
    {"id": "cs_rye", "name": "Corn–soybean + cereal rye cover", "crops": ["corn", "soybeans"], "covers": ["cereal rye"], "needs": {"cover_termination"}},
    {"id": "cso_rc", "name": "Corn–soybean–oats/red clover", "crops": ["corn", "soybeans", "oats"], "covers": ["red clover"], "needs": {"small_grain_market"}},
]
CONSTRAINTS = {
    "small_grain_market": "No local market for small grains (oats)",
    "cover_termination": "Can't manage spring termination of a cover crop",
}
SCORE = {"better": 1, "similar": 0, "worse": -1, "baseline": 0}
GREEN_YEAR_DAYS = 30  # a cover year with >= this many off-season living days counts as "with green"
MEANINGFUL_MONTHS = 0.5


def cell(rating: str, evidence: str, confidence: str, verify: str = "", estimate: str = "") -> dict:
    return {"rating": rating, "evidence": evidence, "confidence": confidence, "verify": verify, "estimate": estimate}


def observed_cover_effect(e1_docs: dict[str, dict]) -> dict | None:
    """Local evidence: no-living-cover share in cover years with vs without off-season green, within the same crop.

    Uses complete cover years from every field provided (fields a few km apart share
    weather). Returns None if no crop has both kinds of year.
    """
    by_crop: dict[str, dict[str, list[tuple[str, int, float]]]] = {}
    for fid, doc in e1_docs.items():
        for s in doc["seasons"]:
            if s.get("cover_year_partial") or s.get("no_living_cover_share") is None or s.get("off_season_living_days") is None:
                continue
            kind = "with" if s["off_season_living_days"] >= GREEN_YEAR_DAYS else "without" if s["off_season_living_days"] <= 5 else None
            if kind:
                by_crop.setdefault(s["crop"], {"with": [], "without": []})[kind].append((fid, s["season"], s["no_living_cover_share"]))
    diffs, used = [], {}
    for crop, d in by_crop.items():
        if d["with"] and d["without"]:
            diffs.append(statistics.median(x[2] for x in d["without"]) - statistics.median(x[2] for x in d["with"]))
            used[crop] = {"with": [(f, y) for f, y, _ in d["with"]], "n_without": len(d["without"])}
    if not diffs:
        return None
    eff = statistics.median(diffs)
    return {"share_reduction": round(eff, 3), "months_per_year": round(eff * 12, 1), "evidence": used}


def _current_months(e1: dict) -> float | None:
    return e1["summary"].get("no_living_cover_months_per_year") if e1 else None


def _months_with_cover_everywhere(e1: dict, effect: dict) -> float | None:
    """Estimated no-living-cover months if every cover year gained the locally observed effect (years already green unchanged)."""
    shares = []
    for s in e1["seasons"]:
        if s.get("cover_year_partial") or s.get("no_living_cover_share") is None:
            continue
        sh = s["no_living_cover_share"]
        if (s.get("off_season_living_days") or 0) < GREEN_YEAR_DAYS:
            sh = max(0.0, sh - effect["share_reduction"])
        shares.append(sh)
    return round(statistics.mean(shares) * 12, 1) if shares else None


def rate_field(static: dict, e1: dict | None, e2: dict | None, cover_effect: dict | None) -> dict:
    """Ratings for every candidate x criterion. Independent of priorities and constraints."""
    soil, terrain = static["soil"], static["terrain"]
    slope = terrain["mean_slope_pct"]["value"]
    p90 = terrain["p90_slope_pct"]["value"]
    s_slope = soil["slopegradwta"]["value"]
    kfact = soil["kwfact"]["value"]
    erosion_importance = "higher" if (s_slope or 0) >= 3 or (p90 or 0) >= 3.5 else "lower"
    slope_txt = f"field mean slope {slope}% (NASADEM, smoothed; V12), 90th percentile {p90}%, SSURGO slope {s_slope}%, K factor {kfact}"

    cur_m = _current_months(e1)
    autumn = e1["summary"].get("autumn_green_seasons", 0) if e1 else 0
    existing_cover = autumn >= 3
    e2a = e2["summary"]["all_seasons"] if e2 else None
    stress_txt = (
        f"a dry or hot sensitive window in {e2a['stress_seasons']} of {e2a['seasons']} recent seasons (expected {e2a['expected_stress_seasons']} from 1991–2020; regional)"
        if e2a else "Engine 2 not available"
    )
    baseline = {k: cell("baseline", "Current rotation; other options are rated against it.", "—") for k in CRITERIA}
    out: dict[str, dict] = {c["id"]: (dict(baseline) if c["id"] == "cs" else {}) for c in CANDIDATES}

    # --- Soil cover and living roots
    if e1 and cover_effect:
        est = _months_with_cover_everywhere(e1, cover_effect)
        gain = (cur_m - est) if (cur_m is not None and est is not None) else None
        rating = "better" if gain is not None and gain >= MEANINGFUL_MONTHS else "similar"
        ev = (
            f"Now about {cur_m} months a year without living cover (Engine 1, NASA HLS 30 m). In nearby cover years with autumn green, "
            f"the share without living cover was {cover_effect['share_reduction']:.2f} lower (≈{cover_effect['months_per_year']} months) than in matched years without it. "
            f"Applied to this field's uncovered years: about {est} months a year."
            + (" Satellite already shows autumn green after corn here in several seasons, so part of the gain is in place." if existing_cover else "")
            + " Lower bound: cereal rye also grows in spring, which the observed (likely winter-killed) cover did not."
        )
        out["cs_rye"]["Soil cover and living roots"] = cell(rating, ev, "moderate", "Whether autumn green on this or nearby fields is a planted cover (confirm with the farmer).", f"~{est} months a year without living cover (now ~{cur_m})")
    else:
        out["cs_rye"]["Soil cover and living roots"] = cell("better", "A winter cover fills the harvest-to-planting window, the largest observed gap.", "low–moderate")
    out["cso_rc"]["Soil cover and living roots"] = cell(
        "better",
        f"Now about {cur_m} months a year without living cover. In the oats year, oats then red clover keep living cover from spring through autumn and into the next spring "
        f"({CATALOGUE['oats']['winter_cover']}). Not observed on these fields, so not quantified.",
        "low–moderate",
        "Clover establishment under oats on this soil.",
    )

    # --- Erosion protection
    for cid, why in (("cs_rye", "winter cover over bare ground"), ("cso_rc", "living cover through most of the small-grain year")):
        out[cid]["Erosion protection"] = cell(
            "better",
            f"Better cover ({why}). Erosion importance here is {erosion_importance}: {slope_txt}.",
            "moderate",
            "Slope and erosion history on the steepest part of the field." if erosion_importance == "higher" else "",
        )

    # --- Water and stress exposure
    out["cs_rye"]["Water and stress exposure"] = cell(
        "similar",
        f"Same cash crops, so the same mid-summer sensitive stages; this field's record shows {stress_txt}. "
        f"Rye {CATALOGUE['cereal rye']['water']}.",
        "low–moderate",
        "Earlier rye termination in dry springs.",
    )
    oats_better = bool(e2a and e2a["stress_seasons"] >= 1)
    out["cso_rc"]["Water and stress exposure"] = cell(
        "better" if oats_better else "similar",
        f"In 1 year of 3 the cash crop is oats, whose sensitive stage ({CATALOGUE['oats']['sensitive_stage']}) comes before the July–August windows of corn and soybeans; "
        f"this field's record shows {stress_txt}. Corn and soybeans occupy 2 of 3 years instead of every year.",
        "low–moderate",
        "Oat sensitive-stage timing locally; clover's late-summer water use.",
    )

    # --- Nitrogen needs
    out["cs_rye"]["Nitrogen needs"] = cell(
        "similar",
        f"Soybean credit unchanged. Cereal rye {CATALOGUE['cereal rye']['nitrogen']}.",
        "moderate",
        "Rye termination timing ahead of corn, or rye ahead of soybeans only.",
    )
    out["cso_rc"]["Nitrogen needs"] = cell("better", f"Red clover is a {CATALOGUE['red clover']['nitrogen']}, in addition to the soybean credit.", "moderate", "Clover stand density before corn.")

    # --- Crop diversity
    def groups(c):
        return {CATALOGUE[x]["group"].split(" (")[0] for x in c["crops"] + c["covers"]}

    cur_n, cur_g = len(CANDIDATES[0]["crops"]), len(groups(CANDIDATES[0]))
    for c in CANDIDATES[1:]:
        n, g = len(c["crops"]) + len(c["covers"]), len(groups(c))
        out[c["id"]]["Crop diversity"] = cell(
            "better" if (n, g) > (cur_n, cur_g) else "similar",
            f"{n} species in {g} functional groups, against {cur_n} species in {cur_g} groups now ({', '.join(c['crops'] + c['covers'])}).",
            "high",
        )

    # --- Workload and complexity
    out["cs_rye"]["Workload and complexity"] = cell("worse", f"Adds autumn seeding and spring termination: {CATALOGUE['cereal rye']['management']}.", "moderate", "Seeding equipment, labour at harvest, termination plan.")
    out["cso_rc"]["Workload and complexity"] = cell("worse", "Adds a third crop to plant, harvest (July) and market or feed, plus clover establishment and termination: more change to operations than a cover crop alone.", "moderate", "Small-grain harvest equipment, storage, local oat market.")

    notes = []
    if existing_cover:
        notes.append(f"Satellite shows autumn green after the crop in {autumn} seasons on this field, consistent with a cover crop already in some years (confirm). If so, the current rotation already includes part of the cover-crop option.")
    return {
        "ratings": out,
        "erosion_importance": erosion_importance,
        "current_no_living_cover_months": cur_m,
        "cover_effect": cover_effect,
        "notes": notes,
        "sources": [SOURCE_NAMES[k] for k in sorted({s for v in CATALOGUE.values() for s in v["sources"]})],
        "not_established": [
            "Yield or profit effects on this field.",
            "Soil organic carbon, nitrogen, phosphorus, pH, compaction or biology.",
            "Whether autumn or spring green is a planted cover, weeds or volunteers (confirm before crediting).",
            "Field-level soil moisture: stress drivers are regional (POWER ~0.5°, SMAP 9 km).",
        ],
    }


# ---------------------------------------------------------------- applied live (priorities, constraints)
def ordered_criteria(priority_order: list[str]) -> list[str]:
    seen, out = set(), []
    for p in list(priority_order) + [p for p in PRIORITIES if p not in priority_order]:
        for c in CRITERIA_FOR_PRIORITY[p]:
            if c not in seen:
                seen.add(c)
                out.append(c)
    return out


def apply_constraints(active: set[str]) -> tuple[list[dict], list[tuple[str, str]]]:
    """Step 1: drop candidates that break a stated hard constraint."""
    kept, dropped = [], []
    for c in CANDIDATES:
        hit = c["needs"] & active
        if hit:
            dropped.append((c["name"], "; ".join(CONSTRAINTS[h] for h in sorted(hit))))
        else:
            kept.append(c)
    return kept, dropped


def rank(ratings: dict, candidates: list[dict], priority_order: list[str]) -> list[dict]:
    """Step 3: order candidates lexicographically by ratings in the farmer's priority order (ties keep catalogue order)."""
    crit = ordered_criteria(priority_order)

    def key(c):
        return tuple(-SCORE[ratings[c["id"]][k]["rating"]] for k in crit)

    return sorted(candidates, key=key)


def what_if(ratings: dict, candidates: list[dict], priority_order: list[str]) -> dict[str, str]:
    """Top-ranked option if each priority were moved to first place (ranking stability)."""
    out = {}
    for p in PRIORITIES:
        order = [p] + [q for q in priority_order if q != p]
        out[p] = rank(ratings, candidates, order)[0]["name"]
    return out
