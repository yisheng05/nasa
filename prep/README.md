# Pre-event data-access checks

`check_access.py` confirms that every NASA data path in handoff §10 is reachable for a point and reports granule and record counts. It computes no indices, GDD or analytics.

```bash
python prep/check_access.py --ancillary --json prep/reports/access.json
```

| Check | Host | Pass condition | Needs login |
|---|---|---|---|
| CMR collections | cmr.earthdata.nasa.gov | HLSL30/S30 v2.0, HLSL30/S30_VI v2.0, MSLSP30NA v011, SPL4SMGP all listed | No |
| HLS VI coverage | cmr.earthdata.nasa.gov | VI granules ≥ 95% of surface-reflectance granules, per sensor per year (otherwise WARN: compute indices from SR) | No |
| MSLSP30NA granules | cmr.earthdata.nasa.gov | One or more granules at the point for each year 2016–2019 | No |
| NASA POWER daily | power.larc.nasa.gov | Every day present for T2M_MAX, T2M_MIN, PRECTOTCORR; no fill values | No |
| AppEEARS products | appeears.earthdatacloud.nasa.gov | HLSL30_VI, HLSS30_VI, SPL4SMGP offered | No |
| Earthdata login (AppEEARS) | appeears.earthdatacloud.nasa.gov | Token issued, then revoked. SKIP without credentials | **Yes** |
| SSURGO *(`--ancillary`)* | sdmdataaccess.sc.egov.usda.gov | Map unit returned for the point. WARN only | No |
| CDL *(`--ancillary`)* | nassgeodata.gmu.edu | County stats returned. WARN only | No |

Options: `--lat`, `--lon` (default 42.0, −93.6, central Iowa), `--years 2016-2025`, `--fips 19169` (Story County, for CropScape), `--json PATH`. Exit code 1 on any FAIL.

## Result on 9 Nov 2026 (run from the cloud dev container, no Earthdata credentials)

- PASS: CMR collections, HLS VI coverage, MSLSP30NA, POWER, AppEEARS products, SSURGO.
- HLS VI vs SR granules at the point (tile T15TVG), 2016–2025: L30 515/516, S30 958/962. The lowest year is still above 98%.
- MSLSP30NA: CMR temporal extent 2016-01-01 to 2019-12-31, with one granule per year.
- SKIP: Earthdata login (no credentials in that environment). **Each team member should run it locally.**
- WARN: CropScape failed TLS verification from that container's network. Run it from a team laptop before relying on the API; the fallback is CDL in Google Earth Engine or a CropScape web download.
