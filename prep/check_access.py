#!/usr/bin/env python3
"""Pre-event data-access smoke test for the Field Shift project.

This checks that the NASA (and optionally USDA) data paths in the handoff
(docs/handoff_v2.md, sections 10 and 18.2) are reachable for a point, and
reports granule and record counts. It computes no indices, GDD or other
analytics: that work starts at the event.

Usage:
    python prep/check_access.py
    python prep/check_access.py --lat 42.0 --lon -93.6 --years 2016-2025
    python prep/check_access.py --ancillary --json prep/reports/access.json

Earthdata credentials (only for the AppEEARS login check) are read from
EARTHDATA_USERNAME / EARTHDATA_PASSWORD, a .env file in the repo root, or
~/.netrc (machine urs.earthdata.nasa.gov). Without them that check is SKIP.

Exit code is 1 if any check FAILs, otherwise 0.
"""

from __future__ import annotations

import argparse
import json
import netrc
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path

import requests

CMR = "https://cmr.earthdata.nasa.gov/search"
POWER = "https://power.larc.nasa.gov/api/temporal/daily/point"
APPEEARS = "https://appeears.earthdatacloud.nasa.gov/api"
SDA = "https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest"
CROPSCAPE = "https://nassgeodata.gmu.edu/axis2/services/CDLService/GetCDLStat"

TIMEOUT = 60
USER_AGENT = "field-shift-access-check/0.1"

# Collections named in handoff section 10, keyed by CMR short name.
COLLECTIONS = {
    "HLSL30": "2.0",
    "HLSS30": "2.0",
    "HLSL30_VI": "2.0",
    "HLSS30_VI": "2.0",
    "MSLSP30NA": "011",
    "SPL4SMGP": None,  # take whatever version CMR returns; report it
}

APPEEARS_PRODUCTS = ("HLSL30_VI", "HLSS30_VI", "SPL4SMGP")
POWER_PARAMS = ("T2M_MAX", "T2M_MIN", "PRECTOTCORR")
VI_COVERAGE_MIN = 0.95
TILE_RE = re.compile(r"^HLS\.[LS]30\.(T\d{2}[A-Z]{3})\.")

PASS, WARN, FAIL, SKIP = "PASS", "WARN", "FAIL", "SKIP"


@dataclass
class Result:
    name: str
    status: str
    detail: str
    data: dict = field(default_factory=dict)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def _err(exc: Exception) -> str:
    return f"{type(exc).__name__}: {str(exc)[:200]}"


# --------------------------------------------------------------------------
# 1. CMR collections
# --------------------------------------------------------------------------
def check_collections(s: requests.Session) -> Result:
    params = [("short_name", sn) for sn in COLLECTIONS] + [("page_size", "50")]
    try:
        r = s.get(f"{CMR}/collections.json", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        entries = r.json()["feed"]["entry"]
    except Exception as exc:  # noqa: BLE001
        return Result("CMR collections", FAIL, f"cmr.earthdata.nasa.gov: {_err(exc)}")

    found: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        found[e["short_name"]].append(
            {
                "version": e.get("version_id"),
                "time_start": (e.get("time_start") or "")[:10],
                "time_end": (e.get("time_end") or "present")[:10],
                "provider": e.get("data_center"),
            }
        )

    missing, lines = [], []
    for sn, want in COLLECTIONS.items():
        hits = [h for h in found.get(sn, []) if want is None or h["version"] == want]
        if not hits:
            missing.append(f"{sn} v{want}" if want else sn)
            continue
        h = hits[0]
        lines.append(f"{sn} v{h['version']} {h['time_start']}..{h['time_end']}")

    status = FAIL if missing else PASS
    detail = "; ".join(lines)
    if missing:
        detail = f"missing: {', '.join(missing)}. Found: {detail}"
    return Result("CMR collections", status, detail, {"collections": dict(found)})


# --------------------------------------------------------------------------
# CMR granule helpers
# --------------------------------------------------------------------------
def _granule_titles(
    s: requests.Session, short_name: str, version: str, lat: float, lon: float, start: str, end: str
) -> list[str]:
    titles: list[str] = []
    page = 1
    while True:
        r = s.get(
            f"{CMR}/granules.json",
            params={
                "short_name": short_name,
                "version": version,
                "point": f"{lon},{lat}",
                "temporal": f"{start}T00:00:00Z,{end}T23:59:59Z",
                "page_size": 2000,
                "page_num": page,
            },
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        batch = [e["title"] for e in r.json()["feed"]["entry"]]
        titles.extend(batch)
        if len(batch) < 2000:
            return titles
        page += 1


def _tile_counts(titles: list[str]) -> Counter:
    c: Counter = Counter()
    for t in titles:
        m = TILE_RE.match(t)
        c[m.group(1) if m else "unknown"] += 1
    return c


# --------------------------------------------------------------------------
# 2. HLS VI coverage vs surface reflectance
# --------------------------------------------------------------------------
def check_hls_vi_coverage(s: requests.Session, lat: float, lon: float, years: range) -> Result:
    table: dict[str, dict[int, dict]] = {}
    short_years: list[str] = []
    tiles_seen: Counter = Counter()
    try:
        for sensor in ("L30", "S30"):
            table[sensor] = {}
            for y in years:
                sr = _granule_titles(s, f"HLS{sensor}", "2.0", lat, lon, f"{y}-01-01", f"{y}-12-31")
                vi = _granule_titles(s, f"HLS{sensor}_VI", "2.0", lat, lon, f"{y}-01-01", f"{y}-12-31")
                sr_tiles = _tile_counts(sr)
                tiles_seen.update(sr_tiles)
                ratio = (len(vi) / len(sr)) if sr else None
                table[sensor][y] = {
                    "sr": len(sr),
                    "vi": len(vi),
                    "ratio": round(ratio, 3) if ratio is not None else None,
                    "sr_by_tile": dict(sr_tiles),
                    "vi_by_tile": dict(_tile_counts(vi)),
                }
                if sr and ratio < VI_COVERAGE_MIN:
                    short_years.append(f"{sensor} {y} ({len(vi)}/{len(sr)})")
    except Exception as exc:  # noqa: BLE001
        return Result("HLS VI coverage", FAIL, f"cmr.earthdata.nasa.gov: {_err(exc)}")

    summary = []
    for sensor, rows in table.items():
        sr_total = sum(r["sr"] for r in rows.values())
        vi_total = sum(r["vi"] for r in rows.values())
        summary.append(f"{sensor} VI/SR {vi_total}/{sr_total}")
    tiles = ", ".join(f"{t}({n})" for t, n in tiles_seen.most_common())
    detail = f"{'; '.join(summary)}; tiles: {tiles}"
    if short_years:
        return Result(
            "HLS VI coverage",
            WARN,
            f"VI below {VI_COVERAGE_MIN:.0%} of SR in: {', '.join(short_years)}. "
            f"Compute indices from SR for those years. {detail}",
            {"by_sensor_year": table},
        )
    return Result("HLS VI coverage", PASS, detail, {"by_sensor_year": table})


# --------------------------------------------------------------------------
# 3. MSLSP30NA (validation phenology) granules per year
# --------------------------------------------------------------------------
def check_mslsp(s: requests.Session, lat: float, lon: float) -> Result:
    counts = {}
    try:
        for y in range(2016, 2020):
            counts[y] = len(_granule_titles(s, "MSLSP30NA", "011", lat, lon, f"{y}-01-01", f"{y}-12-31"))
    except Exception as exc:  # noqa: BLE001
        return Result("MSLSP30NA granules", FAIL, f"cmr.earthdata.nasa.gov: {_err(exc)}")
    missing = [y for y, n in counts.items() if n == 0]
    detail = ", ".join(f"{y}: {n}" for y, n in counts.items())
    if missing:
        return Result("MSLSP30NA granules", FAIL, f"no granule for {missing}. {detail}", {"per_year": counts})
    return Result("MSLSP30NA granules", PASS, f"granules per year at point: {detail}", {"per_year": counts})


# --------------------------------------------------------------------------
# 4. NASA POWER daily weather completeness
# --------------------------------------------------------------------------
def check_power(s: requests.Session, lat: float, lon: float, years: range) -> Result:
    start, end = date(years.start, 1, 1), date(years.stop - 1, 12, 31)
    end = min(end, datetime.now(UTC).date())
    try:
        r = s.get(
            POWER,
            params={
                "parameters": ",".join(POWER_PARAMS),
                "community": "AG",
                "latitude": lat,
                "longitude": lon,
                "start": start.strftime("%Y%m%d"),
                "end": end.strftime("%Y%m%d"),
                "format": "JSON",
            },
            timeout=TIMEOUT * 2,
        )
        r.raise_for_status()
        payload = r.json()
        params = payload["properties"]["parameter"]
        fill = payload.get("header", {}).get("fill_value", -999.0)
    except Exception as exc:  # noqa: BLE001
        return Result("NASA POWER daily", FAIL, f"power.larc.nasa.gov: {_err(exc)}")

    expected = (end - start).days + 1
    per_param = {}
    problems = []
    for p in POWER_PARAMS:
        series = params.get(p, {})
        n_fill = sum(1 for v in series.values() if v is None or v == fill)
        per_param[p] = {"days": len(series), "fill": n_fill}
        if len(series) != expected or n_fill:
            problems.append(f"{p}: {len(series)}/{expected} days, {n_fill} fill")
    span = f"{start}..{end}"
    if problems:
        return Result("NASA POWER daily", WARN, f"{span}: {'; '.join(problems)}", {"per_param": per_param})
    return Result(
        "NASA POWER daily",
        PASS,
        f"{span}: {expected} days x {len(POWER_PARAMS)} params, no fill values",
        {"per_param": per_param},
    )


# --------------------------------------------------------------------------
# 5. AppEEARS product list and Earthdata login
# --------------------------------------------------------------------------
def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _earthdata_creds() -> tuple[str, str] | None:
    user, pw = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if user and pw:
        return user, pw
    try:
        auth = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
    except (FileNotFoundError, netrc.NetrcParseError):
        auth = None
    if auth and auth[0] and auth[2]:
        return auth[0], auth[2]
    return None


def check_appeears_products(s: requests.Session) -> Result:
    try:
        r = s.get(f"{APPEEARS}/product", timeout=TIMEOUT)
        r.raise_for_status()
        offered = {p["ProductAndVersion"] for p in r.json()}
    except Exception as exc:  # noqa: BLE001
        return Result("AppEEARS products", FAIL, f"appeears.earthdatacloud.nasa.gov: {_err(exc)}")
    hits = {want: sorted(p for p in offered if p.split(".")[0] == want) for want in APPEEARS_PRODUCTS}
    missing = [k for k, v in hits.items() if not v]
    detail = ", ".join(v[-1] for v in hits.values() if v)
    if missing:
        return Result("AppEEARS products", FAIL, f"not offered: {missing}. Offered: {detail}", {"products": hits})
    return Result("AppEEARS products", PASS, f"offered: {detail} (MSLSP30NA: download via Earthdata)", {"products": hits})


def check_appeears_login(s: requests.Session) -> Result:
    creds = _earthdata_creds()
    if not creds:
        return Result(
            "Earthdata login (AppEEARS)",
            SKIP,
            "no credentials: set EARTHDATA_USERNAME/PASSWORD in .env or add urs.earthdata.nasa.gov to ~/.netrc",
        )
    try:
        r = s.post(f"{APPEEARS}/login", auth=creds, timeout=TIMEOUT)
        if r.status_code in (400, 401, 403):
            return Result("Earthdata login (AppEEARS)", FAIL, f"login rejected (HTTP {r.status_code}) for user {creds[0]}")
        r.raise_for_status()
        token = r.json()["token"]
        s.post(f"{APPEEARS}/logout", headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT)
    except Exception as exc:  # noqa: BLE001
        return Result("Earthdata login (AppEEARS)", FAIL, f"appeears.earthdatacloud.nasa.gov: {_err(exc)}")
    return Result("Earthdata login (AppEEARS)", PASS, f"token issued and revoked for user {creds[0]}")


# --------------------------------------------------------------------------
# 6. USDA ancillary (opt-in, never FAIL)
# --------------------------------------------------------------------------
def check_ssurgo(s: requests.Session, lat: float, lon: float) -> Result:
    q = f"SELECT mukey FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({lon} {lat})')"
    try:
        r = s.post(SDA, json={"query": q, "format": "JSON"}, timeout=TIMEOUT)
        r.raise_for_status()
        rows = r.json().get("Table", [])
    except Exception as exc:  # noqa: BLE001
        return Result("SSURGO (Soil Data Access)", WARN, f"sdmdataaccess.sc.egov.usda.gov: {_err(exc)}")
    if not rows:
        return Result("SSURGO (Soil Data Access)", WARN, "no map unit returned for point")
    return Result("SSURGO (Soil Data Access)", PASS, f"mukey {rows[0][0]} at point", {"mukeys": [r[0] for r in rows]})


def check_cropscape(s: requests.Session, fips: str, year: int) -> Result:
    try:
        r = s.get(CROPSCAPE, params={"year": year, "fips": fips, "format": "json"}, timeout=TIMEOUT)
        r.raise_for_status()
        body = r.text
    except Exception as exc:  # noqa: BLE001
        return Result("CDL (CropScape)", WARN, f"nassgeodata.gmu.edu: {_err(exc)}")
    return Result("CDL (CropScape)", PASS, f"CDL {year} stats returned for county FIPS {fips} ({len(body)} bytes)")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _parse_years(text: str) -> range:
    a, _, b = text.partition("-")
    start, stop = int(a), int(b or a)
    if stop < start:
        raise argparse.ArgumentTypeError("years must be START-END with END >= START")
    return range(start, stop + 1)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lat", type=float, default=42.0, help="latitude (default: central Iowa, 42.0)")
    ap.add_argument("--lon", type=float, default=-93.6, help="longitude (default: central Iowa, -93.6)")
    ap.add_argument("--years", type=_parse_years, default=_parse_years("2016-2025"), help="e.g. 2016-2025")
    ap.add_argument("--ancillary", action="store_true", help="also check USDA SSURGO and CropScape")
    ap.add_argument("--fips", default="19169", help="county FIPS for the CropScape check (default: Story County, IA)")
    ap.add_argument("--json", type=Path, help="write the full report to this path")
    args = ap.parse_args(argv)

    _load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    s = _session()

    checks = [
        lambda: check_collections(s),
        lambda: check_hls_vi_coverage(s, args.lat, args.lon, args.years),
        lambda: check_mslsp(s, args.lat, args.lon),
        lambda: check_power(s, args.lat, args.lon, args.years),
        lambda: check_appeears_products(s),
        lambda: check_appeears_login(s),
    ]
    if args.ancillary:
        checks += [
            lambda: check_ssurgo(s, args.lat, args.lon),
            lambda: check_cropscape(s, args.fips, args.years.stop - 1),
        ]

    print(f"Field Shift data-access check at ({args.lat}, {args.lon}), years {args.years.start}-{args.years.stop - 1}\n")
    results: list[Result] = []
    for run in checks:
        res = run()
        results.append(res)
        print(f"[{res.status:4}] {res.name}\n       {res.detail}\n", flush=True)

    tally = Counter(r.status for r in results)
    print("Summary: " + ", ".join(f"{k} {tally.get(k, 0)}" for k in (PASS, WARN, FAIL, SKIP)))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "run_date": datetime.now(UTC).date().isoformat(),
            "point": {"lat": args.lat, "lon": args.lon},
            "years": [args.years.start, args.years.stop - 1],
            "results": [asdict(r) for r in results],
        }
        args.json.write_text(json.dumps(report, indent=2, default=str))
        print(f"Report written to {args.json}")

    return 1 if tally.get(FAIL) else 0


if __name__ == "__main__":
    sys.exit(main())
