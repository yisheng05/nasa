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
| `engine2.py` | Engine 2: sensitive windows (corn silking from capped GDD after green-up; soybean around the NDVI peak), POWER day-of-year percentiles vs 1991–2020, stress flags with a 1991–2020 base rate and chance-of-observed, relative vigour (peak + integrated NDVI), Scenario A/B/C; step 6 field-scale check against ECOSTRESS (confirmed flags raise confidence to moderate–high) | Engine 1 + `sources/power.py` (+ `sources/ecostress.py`, `sources/smap.py`) | — |
| `engine3.py` | Engine 3: ordinal ratings (better / similar / worse vs current) with evidence, confidence and what to verify; local cover-crop effect from observed cover years; constraint filter, priority ranking and what-if stability (V9) | Engines 1–2, soil, slope, `crop_catalogue.py` | — |
| `crop_catalogue.py` | Qualitative crop and cover-crop traits (sensitive stage, nitrogen, cover, management) with named extension sources | ISU, PFI, SARE, MCCC | — |
| `sources/ecostress.py` | ECOSTRESS evaporative stress index (70 m) per overpass over the field interior, cloud-masked; exact zeros treated as missing | NASA AppEEARS | Earthdata |
| `sources/smap.py` | SMAP L4 root-zone moisture from AppEEARS point CSVs (daily mean) for V11 | NASA AppEEARS | Earthdata |
| `gdd.py` | Capped maize GDD in °C (V10) | — | — |
| `provenance.py` | `sourced()` wrapper and canonical dataset labels for the evidence JSON | — | — |

All three engines are built. V11 (SMAP vs POWER agreement) runs once the SMAP AppEEARS tasks finish; V4 (silking vs Iowa Crop Progress) is not yet wired. Engine 1 thresholds are provisional (NDVI 0.40 living cover, 0.40 spring green); `tests/test_engine1.py` checks it against synthetic seasons with known answers.
