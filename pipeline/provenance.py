"""Every number in the evidence JSON carries its source dataset and date(s) (handoff §8, V8)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def sourced(value: Any, dataset: str, dates: str | list[str] | None = None, **extra: Any) -> dict:
    """Wrap a value with its provenance."""
    rec = {"value": value, "source": dataset}
    if dates is not None:
        rec["dates"] = dates
    rec.update(extra)
    return rec


def run_stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# Canonical dataset labels, so the UI and the References field use one spelling.
DATASETS = {
    "hls_l30": "NASA HLS L30 v2.0 (Landsat 8/9), LP DAAC",
    "hls_s30": "NASA HLS S30 v2.0 (ESA Copernicus Sentinel-2), LP DAAC",
    "hls_vi": "NASA HLS VI v2.0 (HLSL30_VI / HLSS30_VI), LP DAAC via AppEEARS",
    "power": "NASA POWER daily (community AG), NASA LaRC",
    "power_gwetroot": "NASA POWER GWETROOT (from NASA GMAO MERRA-2), modelled",
    "smap_l4": "NASA SMAP L4 SPL4SMGP v008 root-zone soil moisture, modelled/assimilated",
    "nasadem": "NASADEM (NASA JPL reprocessing of SRTM), 1 arc-second, via Microsoft Planetary Computer",
    "ecostress_esi": "NASA ECOSTRESS ECO_L4T_ESI v002, LP DAAC via AppEEARS",
    "usdm": "U.S. Drought Monitor county statistics (NDMC, University of Nebraska-Lincoln; USDA; NOAA), weekly",
    "cdl": "USDA NASS Cropland Data Layer, via USDA CroplandCROS image service",
    "ssurgo": "USDA NRCS SSURGO, via Soil Data Access",
    "mslsp": "NASA MSLSP30NA v011 (MuSLI phenology), LP DAAC",
}
