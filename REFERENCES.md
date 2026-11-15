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
| SRTM GL1 (SRTMGL1_NC) | NASA LP DAAC | v003 | Field mean slope for erosion protection | [SRTM](https://www.earthdata.nasa.gov/data/instruments/srtm) |
| POWER root-zone soil wetness (GWETROOT, from MERRA-2) | NASA LaRC / GMAO | API v2 | Long-record (1981 onward) moisture baseline and trends | [POWER](https://power.larc.nasa.gov/) |
| ECOSTRESS Evaporative Stress Index (ECO_L4T_ESI) *(stretch)* | NASA JPL / LP DAAC | v002 | Field-scale stress check near silking | [ECOSTRESS](https://ecostress.jpl.nasa.gov/data) |
| GPM IMERG final daily (GPM_3IMERGDF) *(stretch)* | NASA GES DISC | v07 | Heavy-rain days for erosion context | [GPM](https://gpm.nasa.gov/data) |
| NEX-GDDP-CMIP6 *(stretch)* | NASA | — | Climate projections | — |

## Space-agency partner data

| Dataset | Agency | Role | Link |
|---|---|---|---|
| Copernicus Sentinel-2 (via HLS S30) | ESA | Field history at 30 m, harmonised with Landsat | [Copernicus Data Space](https://dataspace.copernicus.eu/) |

Attribution: "Contains modified Copernicus Sentinel data [years]" for HLS S30-derived products.

Access: [AppEEARS](https://appeears.earthdatacloud.nasa.gov/), [Earthdata Search](https://search.earthdata.nasa.gov/), [CMR API](https://cmr.earthdata.nasa.gov/search), [POWER API](https://power.larc.nasa.gov/).

## Ancillary data

| Dataset | Provider | Role | Link |
|---|---|---|---|
| Cropland Data Layer | USDA NASS | Crop sequence and ground truth | [CropScape](https://nassgeodata.gmu.edu/CropScape/) |
| Crop Progress | USDA NASS | Validation of stage estimates (V4) | [NASS](https://www.nass.usda.gov/Publications/National_Crop_Progress/) |
| SSURGO / gSSURGO | USDA NRCS | Soil properties | [Soil Data Access](https://sdmdataaccess.sc.egov.usda.gov/) |
| U.S. Drought Monitor | NDMC (University of Nebraska–Lincoln), USDA, NOAA | Neutral check of Engine 2's dry calls (V13), Story County weekly statistics | [Data services](https://droughtmonitor.unl.edu/DmData/DataDownload.aspx) |
| SoilGrids 2.0 | ISRIC | Soil properties outside the US | [SoilGrids](https://soilgrids.org/) |
| NAIP | USDA FPAC | Drawing demo field polygons | [NAIP](https://naip-usdaonline.hub.arcgis.com/) |
| PRISM *(stretch)* | Oregon State University | Cross-check of POWER temperature and GDD | [PRISM](https://prism.oregonstate.edu/) |
| NASS QuickStats *(stretch)* | USDA NASS | County oat acreage as a market proxy | [QuickStats](https://quickstats.nass.usda.gov/) |
| USDA AMS Market News | USDA AMS | Link for checking local small-grain markets | [Market News](https://www.ams.usda.gov/market-news) |
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
