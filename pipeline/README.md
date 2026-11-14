# pipeline/

Precompute code used by `notebooks/01_precompute.ipynb` (handoff §8, §14).

| Module | What it does | Source | Login |
|---|---|---|---|
| `config.py` | Paths, seasons 2016–2025, thresholds (V1, V2), CDL codes | — | — |
| `fields.py` | Demo-field selection (strict corn/soy alternation in CDL, largest inscribed rectangle) and loading with the 30 m inward buffer | CDL | — |
| `demo_fields.geojson` | The three Story County demo fields, checked on NAIP 2025 | — | — |
| `sources/cdl.py` | Majority CDL class per field per year | USDA CroplandCROS image service (CropScape fails TLS in the cloud container) | No |
| `sources/ssurgo.py` | Area-weighted soil properties | USDA Soil Data Access | No |
| `sources/dem.py` | Field slope (smoothed NASADEM) and a 3DEP lidar reference for V12 | Microsoft Planetary Computer | No |
| `sources/power.py` | Daily T2M_MAX, T2M_MIN, PRECTOTCORR, GWETROOT, 1981–2025 | NASA POWER | No |
| `sources/appeears.py` | Submit-or-resume AppEEARS tasks by name, poll, download | NASA AppEEARS | Earthdata |
| `sources/hls.py` | Per-date field NDVI from AppEEARS HLS outputs, Fmask QC, V1/V2 | NASA HLS v2.0 | Earthdata |
| `engine1.py` | Engine 1: Whittaker smoothing, green-up/peak/decline, living vs no-living-cover days per cover year, off-season living days, spring/autumn green, confidence | from `sources/hls.py` | — |
| `gdd.py` | Capped maize GDD in °C (V10) | — | — |
| `provenance.py` | `sourced()` wrapper and canonical dataset labels for the evidence JSON | — | — |

Still to build: Engine 2 stress windows, Engine 3 ratings. Engine 1 thresholds are provisional (NDVI 0.40 living cover, 0.40 spring green); `tests/test_engine1.py` checks it against synthetic seasons with known answers.
