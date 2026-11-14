"""NASA AppEEARS client: submit-or-resume tasks by name, poll, download.

Credentials come from EARTHDATA_USERNAME/EARTHDATA_PASSWORD or ~/.netrc
(machine urs.earthdata.nasa.gov). Tokens are kept in memory only.
"""

from __future__ import annotations

import netrc
import os
import time
from fnmatch import fnmatch
from pathlib import Path

import requests

API = "https://appeears.earthdatacloud.nasa.gov/api"
TIMEOUT = 120
_token: str | None = None


def _creds() -> tuple[str, str]:
    user, pw = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if user and pw:
        return user, pw
    auth = netrc.netrc().authenticators("urs.earthdata.nasa.gov")
    if not auth:
        raise RuntimeError("No Earthdata credentials (env or ~/.netrc)")
    return auth[0], auth[2]


def token() -> str:
    global _token
    if _token is None:
        r = requests.post(f"{API}/login", auth=_creds(), timeout=TIMEOUT)
        r.raise_for_status()
        _token = r.json()["token"]
    return _token


def _h() -> dict:
    return {"Authorization": f"Bearer {token()}"}


def tasks() -> list[dict]:
    r = requests.get(f"{API}/task", headers=_h(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def find_task(name: str) -> dict | None:
    live = [t for t in tasks() if t.get("task_name") == name and t.get("status") not in ("error", "deleted")]
    live.sort(key=lambda t: t.get("created", ""), reverse=True)
    return live[0] if live else None


def submit(task: dict) -> dict:
    """Submit unless a non-failed task with the same name already exists. Returns the task record."""
    existing = find_task(task["task_name"])
    if existing:
        return existing
    r = requests.post(f"{API}/task", json=task, headers=_h(), timeout=TIMEOUT)
    if r.status_code >= 400:
        raise RuntimeError(f"AppEEARS rejected {task['task_name']}: HTTP {r.status_code} {r.text[:500]}")
    return {"task_id": r.json()["task_id"], "task_name": task["task_name"], "status": "pending"}


def status(task_id: str) -> dict:
    r = requests.get(f"{API}/task/{task_id}", headers=_h(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def wait(task_id: str, every_s: int = 30, max_s: int = 3600) -> dict:
    t0 = time.time()
    while True:
        s = status(task_id)
        if s.get("status") in ("done", "error") or time.time() - t0 > max_s:
            return s
        time.sleep(every_s)


def bundle(task_id: str) -> list[dict]:
    r = requests.get(f"{API}/bundle/{task_id}", headers=_h(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["files"]


def _fetch(task_id: str, f: dict, out: Path) -> Path:
    if out.exists() and out.stat().st_size == f.get("file_size", -1):
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(f"{API}/bundle/{task_id}/{f['file_id']}", headers=_h(), stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        tmp = out.with_suffix(out.suffix + ".part")
        with open(tmp, "wb") as fh:
            fh.writelines(r.iter_content(1 << 20))
        tmp.rename(out)
    return out


def download(task_id: str, dest: Path, patterns: tuple[str, ...] = ("*",), workers: int = 12) -> list[Path]:
    """Download bundle files matching any glob pattern, in parallel; skip files already present."""
    from concurrent.futures import ThreadPoolExecutor

    dest.mkdir(parents=True, exist_ok=True)
    token()  # log in once before the threads start
    wanted = [f for f in bundle(task_id) if any(fnmatch(f["file_name"], p) for p in patterns)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(lambda f: _fetch(task_id, f, dest / f["file_name"]), wanted))


# --------------------------------------------------------------------------
# Task builders for this project
# --------------------------------------------------------------------------
def _dates(start: str, end: str, recurring: tuple[int, int] | None = None) -> list[dict]:
    d = {"startDate": start, "endDate": end}
    if recurring:
        d.update({"recurring": True, "yearRange": list(recurring)})
    return [d]


def hls_task(
    name: str,
    feature_collection: dict,
    sensors: tuple[str, ...] = ("L30", "S30"),
    vi_layers: tuple[str, ...] = ("NDVI",),
    start="01-01-2016",
    end="12-31-2025",
) -> dict:
    """HLS VI layers plus Fmask from the surface-reflectance product (the VI product has no QA layer).

    AppEEARS caps files per task, so callers split by field, sensor and period (see hls_tasks).
    """
    layers = []
    for sensor in sensors:
        layers += [{"product": f"HLS{sensor}_VI.020", "layer": lyr} for lyr in vi_layers]
        layers.append({"product": f"HLS{sensor}.020", "layer": "Fmask"})
    return {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": _dates(start, end),
            "layers": layers,
            "geo": feature_collection,
            "output": {"format": {"type": "geotiff"}, "projection": "native"},
        },
    }


def hls_tasks(feature_collection: dict, periods=((2016, 2020), (2021, 2025)), version="v1") -> list[dict]:
    """One task per field x sensor x period, which keeps each under the AppEEARS file cap."""
    out = []
    for feat in feature_collection["features"]:
        fc1 = {"type": "FeatureCollection", "features": [feat]}
        fid = feat["properties"]["id"]
        for sensor in ("L30", "S30"):
            for y0, y1 in periods:
                out.append(
                    hls_task(
                        f"fieldshift_hls_{sensor.lower()}_{fid}_{y0}_{y1}_{version}",
                        fc1,
                        sensors=(sensor,),
                        start=f"01-01-{y0}",
                        end=f"12-31-{y1}",
                    )
                )
    return out


def esi_tasks(feature_collection: dict, version="v1") -> list[dict]:
    out = []
    for feat in feature_collection["features"]:
        fid = feat["properties"]["id"]
        out.append(esi_task(f"fieldshift_esi_{fid}_{version}", {"type": "FeatureCollection", "features": [feat]}))
    return out


def esi_task(name: str, feature_collection: dict) -> dict:
    return {
        "task_type": "area",
        "task_name": name,
        "params": {
            "dates": _dates("06-01", "09-15", recurring=(2018, 2025)),
            "layers": [{"product": "ECO_L4T_ESI.002", "layer": lyr} for lyr in ("ESI", "cloud")],
            "geo": feature_collection,
            "output": {"format": {"type": "geotiff"}, "projection": "native"},
        },
    }


def smap_point_task(name: str, points: list[dict], start="04-01-2015", end="12-31-2025") -> dict:
    return {
        "task_type": "point",
        "task_name": name,
        "params": {
            "dates": _dates(start, end),
            "layers": [{"product": "SPL4SMGP.008", "layer": "Geophysical_Data_sm_rootzone"}],
            "coordinates": points,
        },
    }
