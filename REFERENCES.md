# References

Keep this file current. It feeds the submission's **Space Agency Data** and **References** fields (handoff §1.4).

## Space-agency data (NASA)

| Dataset | Provider | Version | Role | Link |
|---|---|---|---|---|
| HLS L30 / S30 surface reflectance + Fmask | NASA LP DAAC | v2.0 | Field history (core) | [HLS data](https://hls.gsfc.nasa.gov/hls-data) |
| HLS L30 / S30 Vegetation Indices | NASA LP DAAC | v2.0 | NDVI, EVI, NBR2 (core) | [HLSL30_VI](https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlsl30-vi-2.0) · [HLSS30_VI](https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlss30-vi-2.0) |
| MSLSP30NA (MuSLI) phenology | NASA LP DAAC | v011, 2016–2019 | Validation of Engine 1 | [catalogue](https://www.earthdata.nasa.gov/data/catalog/lpcloud-mslsp30na-011) |
| SMAP L4 surface and root-zone soil moisture (SPL4SMGP) | NASA GMAO / NSIDC | v008 | Root-zone moisture anomaly (regional, 9 km) | [NSIDC](https://nsidc.org/data/spl4smgp) |
| POWER daily meteorology | NASA LaRC | API v2 | Temperature and rainfall anomalies, GDD (regional, ~0.5°) | [POWER](https://power.larc.nasa.gov/) |
| GPM IMERG *(optional)* | NASA | — | Finer rainfall | — |
| NEX-GDDP-CMIP6 *(stretch)* | NASA | — | Climate projections | — |

Access: [AppEEARS](https://appeears.earthdatacloud.nasa.gov/), [Earthdata Search](https://search.earthdata.nasa.gov/), [CMR API](https://cmr.earthdata.nasa.gov/search), [POWER API](https://power.larc.nasa.gov/).

## Ancillary data

| Dataset | Provider | Role | Link |
|---|---|---|---|
| Cropland Data Layer | USDA NASS | Crop sequence and ground truth | [CropScape](https://nassgeodata.gmu.edu/CropScape/) |
| Crop Progress | USDA NASS | Validation of stage estimates (V4) | [NASS](https://www.nass.usda.gov/Publications/National_Crop_Progress/) |
| SSURGO / gSSURGO | USDA NRCS | Soil properties | [Soil Data Access](https://sdmdataaccess.sc.egov.usda.gov/) |
| SoilGrids 2.0 | ISRIC | Soil properties outside the US | [SoilGrids](https://soilgrids.org/) |
| OpTIS | CTIC / TNC / Regrow | Context only | [OpTIS 2.0](https://www.farmprogress.com/crops/optis-20-adds-geography-cropping-seasons-and-search-options) |

## Rules and guidance

- NASA Space Apps 2026 [Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/), [2026 event page](https://www.spaceappschallenge.org/2026/), [Project Submission Guide](https://www.spaceappschallenge.org/resources/project-submission-guide/), [Judging & Awards Guide](https://www.spaceappschallenge.org/resources/judging-awards-guide)

## Research and agronomy

- Bowles, T. M. et al. (2020). Long-term evidence shows that crop-rotation diversification increases agricultural resilience to adverse growing conditions in North America. *One Earth* 2(3). DOI: [10.1016/j.oneear.2020.02.007](https://doi.org/10.1016/j.oneear.2020.02.007)
- Seifert, C. A., Azzari, G. & Lobell, D. B. (2018). Satellite detection of cover crops and their effects on crop yield in the Midwestern United States. *Environmental Research Letters* 13. [link](https://fse.fsi.stanford.edu/node/28583)
- Purdue Extension NCH-40: Corn growing degree days. [link](https://www.extension.purdue.edu/extmedia/nch/nch-40.html)
- USDA NRCS: Soil health principles.

## Code and libraries

See `requirements.txt`. Add any third-party code copied or adapted here, with a link and its licence.

## AI tools used

| Tool | Used for |
|---|---|
| Claude Code (Anthropic) | Pre-event: repo setup, README, rules checklist, this file, the data-access check script (9 Nov); research on 2026 rules and revision of the design handoff to v2.1 (13 Nov) |
| | *(add tools used during the event)* |
