"""Paths and constants shared by the precompute notebooks."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
DEMO_FIELDS = REPO / "pipeline" / "demo_fields.geojson"

SEASONS = range(2016, 2026)  # 2016-2025 inclusive (handoff §3.2)
CLIMATE_BASELINE = (1991, 2020)  # POWER day-of-year percentiles (handoff §8.2)
POWER_START = 1981

ALBERS = 5070  # CONUS Albers, CDL's native CRS; metres
WGS84 = 4326
PIXEL_M = 30.0
INWARD_BUFFER_M = 30.0  # one HLS pixel (handoff §8.1 step 2)
MIN_VALID_PIXELS = 50  # V1
MIN_SEASON_OBS = 8  # V2, April-October

# CDL class codes used here (USDA NASS CDL legend)
CDL_CLASSES = {
    1: "corn", 5: "soybeans", 24: "winter wheat", 26: "dbl crop winwht/soy", 28: "oats",
    36: "alfalfa", 37: "other hay", 61: "fallow/idle", 111: "open water", 121: "developed/open",
    122: "developed/low", 123: "developed/med", 124: "developed/high", 141: "deciduous forest",
    176: "grassland/pasture", 190: "woody wetlands", 195: "herbaceous wetlands",
}
CORN, SOY = 1, 5

for _d in (RAW, PROCESSED):
    _d.mkdir(parents=True, exist_ok=True)
