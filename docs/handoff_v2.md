# NASA Space Apps 2026: Field Shift Hackathon Handoff (v2)

**Version:** v2.1, 13 November 2026 (v2: 6 November 2026). Replaces v1 (in-season crop monitoring and alerting). Changes in v2.1 are listed in §0.1.
**Challenge page:** [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=details)
**Hackathon:** Saturday 14 – Sunday 15 November 2026

---

## 0. Why v2 exists

v1 was a well-reasoned design for a different problem. The brief asks for a tool that helps farmers **explore crop rotation strategies** using NASA data, **local soil information**, **crop characteristics** and **farmer priorities**, so that they can **strengthen soil health** and **adapt to changing conditions**. v1 designed an in-season monitoring and alerting system. It mentioned rotation only as something that distorts the baseline, treated soil only as a store of water, and had no input for the farmer's priorities.

v2 keeps v1's analytical core and points it at past seasons instead of the current one. The field's own history becomes the evidence base for a multi-year rotation decision.

| v1 section | Treatment in v2 |
|---|---|
| §1–2 Executive recommendation, product concept | Rebuilt (§2–3) |
| §3 Domain model | Kept and condensed; soil health and rotation added (§4) |
| §4 Weather, climate and adaptation | Kept; re-centred on the strategic horizon (§5) |
| §5 Core variables | Kept; extended (§6) |
| §6 Estimating crop stage | Kept; **GDD formula corrected** (§7) |
| §7 Phenology and stress engines | Rebuilt as three engines (§8) |
| §8 Sensor-fusion scenarios | Kept; reframed for past seasons, two scenarios added (§9) |
| §9 Spatial and temporal resolution | Kept; driver-resolution caveat added (§11) |
| §10 Alerting strategy | **Moved to future work** (§21) |
| §11 Responsible-AI principles | Kept; updated for rotation decisions (§12) |
| §12–13 MVP, architecture | Rebuilt (§13–14) |
| §14 Assumptions and failure modes | Updated (§16) |
| §15 Learning plan | Updated (§18) |
| §16 Demo narrative | Rebuilt, with a short cut for the global submission (§19) |
| New | Challenge text and rules (§1), data sources (§10), validation plan with acceptance criteria (§15) |

### 0.1 Changes in v2.1 (13 November 2026)

| Change | Why | Sections |
|---|---|---|
| **Pre-work rule is now explicit for 2026.** The 2026 Participant FAQ says teams "are not allowed to begin working on the challenges prior to the hackathon". | Retrieved 13 Nov via the search index of the official FAQ; the live page returned HTTP 503 to automated fetches. Verify the wording on the page. | §1.4, §18, §23 |
| Challenge Resources are published on 13 November. | 2026 FAQ (same source). The Resources tab could not be retrieved on 13 Nov; it must be read manually and folded into §10. | §1.1, §1.3, §10, §18.2 |
| The first judging criterion was named **Impact** in the 2025 guide ("Influence" in 2024). | 2025 Project Submission Guide via the search index. 2026 wording not yet confirmed. | §1.5 |
| Submission mechanics from the 2025 guide: the Project tab appears only when the hackathon begins, every team must submit a Project Demo, a submission is final after the deadline, and submitting is required for a certificate and Global Judging. | 2025 guide via the search index. | §1.4 |
| "Bare-soil days" renamed **no-living-cover days**. | Residue and snow also cover soil; the satellite evidences the absence of green vegetation, not bare soil (§3.4). | §3, §6, §8, §9, §13–15, §19 |
| Winter-cover flag replaced by a **spring-cover flag** (1 March to cash-crop green-up). | In Iowa, November–February has snow masking and few valid scenes; cereal rye is mostly visible from mid-March to April, before termination. | §8.1, §9, §13.3, §14 |
| Small-sample caveat added to V3 and to crop-specific baselines. | About five corn seasons per field and four MSLSP30NA years (2016–2019). Report n; present as sanity checks. | §15, §16.3 |
| Data checks recorded: MSLSP30NA confirmed 2016–2019 and not offered in AppEEARS; HLS VI coverage confirmed on tile T15TVG for 2016–2025. | `prep/check_access.py` run on 9 Nov. | §10, §18.2 |

---

## 1. The challenge, the rules and the dates

### 1.1 Challenge text

> Farmers around the world navigate shifting temperatures, changing rainfall patterns, water shortages, extreme weather, and declining soil health. These pressures make it difficult to choose crop rotations that protect fields, conserve water, and support long‑term resilience. Your challenge is to create a decision‑support tool that uses NASA Earth observations along with local soil information, crop characteristics, and farmer priorities to help farmers explore rotation strategies that could strengthen soil health and adapt their farms to changing conditions.

**Update 13 Nov:** the official page returned HTTP 503 to automated fetches and could not be compared with this text. Resources for each challenge are published on 13 November (2026 FAQ). **Read the Details and Resources tabs manually and record any differences in `docs/rules_check_2026.md`.**

**Provenance:** this text is quoted from the public repositories of two teams working this challenge ([FieldShift-NASA](https://github.com/sagar25446-prog/FieldShift-NASA), last verified 14 Oct 2026; [farmstack](https://github.com/anirban-islam/farmstack)). The official page blocks automated fetches. **Confirm it on the challenge page, including the Resources tab, before the event.**

### 1.2 What the brief requires

| Phrase in the brief | What it means for the product | Where it is handled |
|---|---|---|
| "shifting temperatures, changing rainfall… declining soil health" | The pressures the tool must evidence for a specific field | §8 Engines 1–2, §9 |
| "protect fields, conserve water, and support long-term resilience" | The three outcomes rotations are compared on | §8 Engine 3 |
| "NASA Earth observations" | The core evidence, visibly NASA-sourced | §10 |
| "local soil information" | An input, prefilled and editable by the farmer | §8 Engine 3, §13 |
| "crop characteristics" | A catalogue of crop traits that drive the comparison | §8 Engine 3 |
| "farmer priorities" | An input that reorders the trade-offs without changing the evidence | §8 Engine 3 |
| "explore rotation strategies" | Compare options; do not prescribe one | §3, §8 Engine 3 |
| "could strengthen soil health" | A modest claim based on how rotations work, not on measured soil change | §3, §4.6 |
| "adapt their farms to changing conditions" | Trends at the location, and stress that recurs across seasons | §8 Engine 2, §9 |

"Conserve water" means different things in different places. On a rainfed Iowa field it means soil water-holding capacity and exposure to mid-season dry spells. On an irrigated field in Punjab it means groundwater pumped. The chosen geography decides which.

### 1.3 Key dates

- **Hackathon:** Saturday 14 – Sunday 15 November 2026.
- **Challenge Resources published:** Friday 13 November (2026 FAQ).
- **Submission window:** opens Saturday 14 November at 9:00 am; closes Sunday 15 November at 11:59 pm local time ([Space Apps 2026](https://www.spaceappschallenge.org/2026/)).
- **Project Submission and Judging & Awards guides:** published Friday 13 November ([Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/)).

### 1.4 Rules (updated 13 November)

The pre-work rule below is from the 2026 FAQ. The other points come from earlier years; confirm each against the 2026 guides.

- **Work before the event (2026, explicit).** The 2026 Participant FAQ states that "Teams are not allowed to begin working on the challenges prior to the hackathon" ([Participant FAQs](https://www.spaceappschallenge.org/resources/participant-faqs/); retrieved via search index on 13 Nov, verify on the page). Team formation and contact with Local Leads before the event are allowed. The 2022 FAQ said the same in softer terms ([legacy FAQ](https://legacy.spaceappschallenge.org/resources/faq/)). Other teams' public pre-event code is not permission. Implications:
  - Write all product code (engines, UI, the precompute notebook) from the start of the hackathon.
  - This repo already contains pre-event material: this handoff, a rules checklist, a references file and a data-access smoke test (commit of 9 Nov). Ask the Local Lead in writing on 13 Nov whether that is acceptable, and **disclose it in the submission** (see the README's pre-event log). Don't hide or backdate it.
  - Unless the Local Lead says otherwise, don't build the submitted pipeline on top of `prep/check_access.py`; treat it as setup tooling.
- **Submission mechanics (2025 guide; confirm for 2026).** The Project tab on the team page appears only when the hackathon begins. Every team must submit a Project Demo. Submissions are final after the deadline, with no edits. Submitting is required for a participant certificate and for Global Judging.
- **Demo format.** In 2022 the demo was either a video of up to 30 seconds or a deck of up to 7 slides, and judges stopped reviewing at the limit ([2022 Submission Guide](https://spaceapps-prod.s3.amazonaws.com/media/documents/Space_Apps_2022_Project_Submission_Guide.pdf)). Plan both a 30-second cut and the longer local pitch.
- **NASA data.** Projects had to use some open data from NASA or a partner space agency and explain how in a "Space Agency Data" field.
- **References.** All data, code, text, images and tools had to be listed. List the AI tools used as well.
- **Team size.** 1–6 members in 2024 ([Judging & Awards Guide](https://spaceappschallenge.org/resources/judging-awards-guide)).

### 1.5 Judging criteria

The questions below are from the 2024 guide ([Judging & Awards Guide](https://spaceappschallenge.org/resources/judging-awards-guide)). The 2025 Project Submission Guide names the five criteria **Impact, Creativity, Validity, Relevance and Presentation**. Confirm the 2026 names and questions.

| Criterion | Judges' question (2024) | What it means for us |
|---|---|---|
| Impact (2025; "Influence" in 2024) | How much influence can this project have? (2024) | Show how the pipeline transfers beyond one US field (§19) |
| Creativity | Is the approach novel? | Field-scale history from 30 m data, where most tools use coarse grids |
| Validity | Is the solution scientifically valid? Can it work in the real world? | A validation chart, stated limits, honesty about resolution (§15) |
| Relevance | Is the project responsive to the challenge? Is it complete and feasible? | Every screen maps to a phrase in the brief (§1.2) |
| Presentation | Did the team tell the story well? | One farmer, one field, one rotation decision |

---

## 2. Executive recommendation

Treat the 48 hours as a **product-discovery and geospatial prototype sprint**, not a coding contest. Build a **rotation-exploration tool whose evidence is the field's own history**.

The strongest solution is likely to:

1. Focus on one farmer, one field and one rotation decision.
2. Show what the field has actually done over 6–10 seasons: crop sequence, timing, how long the soil was covered, and recurring stress. This uses 30 m NASA HLS data.
3. Show how conditions are changing at that location.
4. Take soil information and the farmer's priorities as inputs.
5. Compare 2–4 candidate rotations as trade-offs, giving the evidence and confidence for each rating, and not name a single "optimal" rotation.
6. State plainly what satellites can and cannot establish about soil health.

Guiding principle (replaces v1's "notify only when the decision should change"):

> **Show what the field has done, what is changing, and what each rotation trades off. Leave the choice with the farmer.**

### Positioning

At least three teams have public repositories for this challenge already ([FieldShift-NASA](https://github.com/sagar25446-prog/FieldShift-NASA), [farmstack](https://github.com/anirban-islam/farmstack), [AgroScope](https://github.com/Zahin-Tajwar/AgroScope)). The ones reviewed rely mostly on coarse climate grids (NASA POWER at about 0.5°, SMAP at 9 km) and MODIS-scale vegetation data (250–500 m). Two list Landsat among their planned sources. The most developed one uses weighted scoring over crop-compatibility rules. That approach is crowded. Our differentiator is **field-scale evidence from 30 m HLS data**: what this specific field did, season by season. This is an inference from three repositories, not a survey of every team.

---

## 3. Product concept: Field History → Rotation Options

### 3.1 The six questions

| # | Question | Evidence | Origin |
|---|---|---|---|
| 1 | What has this field grown, and when? | Crop sequence; green-up, peak and harvest per season | v1 phenology, run on past seasons |
| 2 | How long was the soil covered, and by living plants? | Living-cover days, no-living-cover days, spring green cover | New, from the same time series |
| 3 | Where did stress recur, and at which crop stage? | Expected vs observed development; deficits near sensitive stages | v1 stress engine, run on past seasons |
| 4 | How are conditions changing here? | Trends in heat, rainfall and root-zone moisture; optional projections | v1 weather vs climate |
| 5 | What do the soil and the farmer's priorities rule in or out? | Soil properties, farmer-stated priorities and constraints | New |
| 6 | How do candidate rotations compare against those priorities, and how sure are we? | Trade-off table with evidence and confidence | New |

### 3.2 Primary user and decision (recommended)

**User:** a row-crop farmer in central Iowa growing corn and soybean in alternate years, mostly rainfed.

**Decision:** for next season and beyond, should this field:

- stay corn–soybean;
- stay corn–soybean and add a winter cover crop (for example, cereal rye); or
- extend to a three- or four-year rotation that adds a small grain (for example, oats followed by clover)?

**Timing:** the hackathon falls in the post-harvest planning window, when this decision is actually made. The demo can open with "It's November, and this farmer is planning next year."

**Why Iowa:** ground truth makes Validity demonstrable. Crop type per 30 m pixel comes from USDA's Cropland Data Layer every year since 2008. Weekly stage percentages come from NASS Crop Progress. Soil properties come from SSURGO. A NASA 30 m phenology product (MSLSP30NA) covers 2016–2019.

**What would change this recommendation:**

- If the team wants a stronger Influence story for smallholders in the Global South, choose the rice–wheat system in Punjab or Haryana. It has a sharper soil-health and groundwater story, and the dry winter wheat season suits optical imagery. But there is no equivalent of the Cropland Data Layer for ground truth, and monsoon cloud leaves large gaps during the rice season.
- Southeast Asian rice would make a natural local story for a Singapore-based team. Persistent cloud, though, makes optical 30 m time series sparse. It would need radar data, which is out of scope for 48 hours.

### 3.3 Problem statement

> Farmers choosing crop rotations must weigh soil protection, water use and resilience to a changing climate. The evidence for their own field is scattered across technical datasets: what it has grown, how long its soil went without living cover, when stress recurred, and how local conditions are shifting. The proposed tool reconstructs a field's history from NASA Earth observations. It combines that history with local soil information, crop characteristics and the farmer's stated priorities, and compares candidate rotations as explicit trade-offs with stated confidence.

### 3.4 What the product should not claim

- It should not claim to measure soil organic carbon, nitrogen, phosphorus, pH, compaction or soil biology from space.
- It should not predict yield or profit for a rotation on this field. Published rotation effects (§4.7) are context, not a forecast.
- It should not name a single optimal rotation. It ranks options only against priorities the farmer set, and shows what changes when those priorities change.
- It should not treat low off-season NDVI as proof of bare soil. Crop residue, snow and a newly planted crop also read low.
- It should not treat high off-season NDVI as proof of a cover crop. Weeds and volunteer plants also read green.
- It should not present regional driver data (9 km soil moisture, 0.5° weather) as field measurements.
- It should not use an LLM to generate evidence, thresholds, ratings or recommendations.

Use labels such as **estimated**, **consistent with**, **likely** and **field check recommended**.

---

## 4. Domain model

Treat agriculture as a decision system:

> **Environment → crop condition → yield risk → farmer decision → outcome**

Satellite data mostly observes the left-hand side. A rotation decision is on the right-hand side, made once a year and with effects that build over several years.

### 4.1 Soil (kept from v1)

Soil provides water, nutrients and the environment for roots.

- **Saturation:** the pores are full of water, and roots can be starved of oxygen.
- **Field capacity:** excess water has drained away, but useful water remains.
- **Wilting point:** the water left is held too tightly for plants to extract.
- **Plant-available water:** roughly field capacity minus wilting point (available water capacity, AWC, in soil surveys).

Sandy soils drain quickly; clay-rich soils hold more water. The same rainfall does not produce the same outcome everywhere. Much of Iowa's cropland is tile-drained, which changes how soil moisture behaves after heavy rain.

### 4.2 Water (kept)

Water enters as rain and irrigation. It leaves as runoff, drainage, evaporation and transpiration. **Evapotranspiration (ET)** combines evaporation and transpiration, and must be read alongside crop stage and the water available.

### 4.3 Temperature and energy (kept)

Each crop grows within its own temperature range. Heat raises water demand and can cause heat stress. **High temperature + below-normal rainfall + low soil moisture** tells you more than any one of these alone.

### 4.4 Vegetation condition (kept)

`NDVI = (NIR - Red) / (NIR + Red)`

NDVI tracks greenness and canopy density. EVI reduces soil-background effects and stays more sensitive in dense canopies. Vegetation indices are observations, not diagnoses.

The shortwave-infrared bands add a second signal. The **normalised difference tillage index**, `NDTI = (SWIR1 - SWIR2) / (SWIR1 + SWIR2)`, is used as a proxy for crop residue cover. It has exactly the same formula as **NBR2**, one of the nine indices in NASA's HLS vegetation-index product. It is sensitive to soil moisture and to green vegetation, so treat it as a stretch signal that needs calibration.

### 4.5 Time and lifecycle (kept)

> Planting → emergence → vegetative growth → flowering → grain fill → maturity → harvest

Sensitivity to stress changes with stage. Maize is most sensitive to water stress around silking and pollination. Soybean is most sensitive during pod set and seed fill.

### 4.6 Soil health (new)

Soil health is the continued capacity of soil to function: holding water, cycling nutrients, supporting roots and resisting erosion. USDA NRCS frames it as four management principles: **minimise disturbance, maximise soil cover, maximise biodiversity, maintain continuous living roots**.

| Soil-health indicator | Observable from satellite? | Source in this tool |
|---|---|---|
| Soil cover by living plants | Yes, as days of green cover | HLS NDVI/EVI time series |
| Soil cover by residue | Partly; needs calibration | HLS SWIR index (NDTI/NBR2), stretch goal |
| Continuous living roots | As a proxy: days with green vegetation | HLS time series |
| Crop diversity | Yes | Crop sequence (CDL in the US) |
| Disturbance (tillage) | Partly | Residue proxy; OpTIS aggregates for context |
| Organic carbon, N, P, pH, aggregate stability, compaction, biology | **No** | Farmer soil tests, SSURGO or SoilGrids estimates |

This table is the core of the Validity story: the tool evidences management **practices** that are known to build soil health, and does not claim to measure soil health itself.

### 4.7 Crop rotation (new)

**Why rotations matter:**

- They break pest, disease and weed cycles. Continuous corn, for example, builds up corn rootworm pressure.
- Legumes fix nitrogen. Soybean, alfalfa and clover leave nitrogen credits for the following crop.
- Different crops leave different amounts of residue and root at different depths, which changes soil structure and carbon inputs.
- Different crops need water at different times. A crop whose sensitive stage falls outside the field's usual dry spell reduces exposure.
- Cover crops fill the gap between cash crops. They add soil cover and living roots, and reduce erosion and nitrate loss.

**Evidence to cite as context, not as a forecast for this field:**

- **Diversified rotations and resilience.** Bowles et al. (2020) analysed 347 site-years from 11 long-term experiments in the US and Canada. More diverse rotations raised maize yields by 28.1% on average across growing conditions, and by 22.6% even in favourable ones. They also reduced drought-year yield losses by 14.0–89.9%, depending on the site ([Bowles et al. 2020, *One Earth*](https://par.nsf.gov/servlets/purl/10331499)). This is the strongest published link between the brief's "rotation" and "adapt to changing conditions".
- **Cover crops seen from space.** Seifert, Azzari and Lobell (2018) detected winter vegetation on Midwestern maize and soybean fields with 91.5% accuracy. After controlling for soil quality, they found only modest average yield gains: 0.65% for maize and 0.35% for soybean ([Seifert et al. 2018, *ERL*](https://fse.fsi.stanford.edu/node/28583)). The case for cover crops therefore rests on protecting the soil more than on short-term yield. The tool should frame them that way.

**Trade-offs are real.** That is why the farmer's priorities belong in the tool:

- Diversified rotations need different equipment, markets and labour.
- Small grains often earn less gross revenue.
- Cover crops cost seed and management time. Cereal rye ahead of corn needs careful termination timing.
- On rented land, which is common in Iowa, the person farming may not control or benefit from long-term soil investments.

---

## 5. Weather, climate and adaptation

### 5.1 Three decision horizons

| Horizon | Timeframe | Example decisions | In this product |
|---|---:|---|---|
| Operational | Hours to weeks | Irrigate, inspect, prioritise scarce water | Out of scope (future work, §21) |
| Tactical | Weeks to a season | Planting date, hybrid maturity | Secondary: options within a rotation |
| **Strategic** | **Several seasons to years** | **Rotation, crop mix, cover crops, infrastructure** | **Primary** |

> **Field history + recurring stress + local climate trend → rotation trade-offs**

### 5.2 Adaptation chain (kept, with a rotation example)

`hazard → exposure → vulnerability → impact → adaptation`

Example: dry spells around midsummer → maize on the field every other year, with silking in that window → soil with modest water-holding capacity → yield-loss risk in corn years → options:

- shift hybrid maturity or planting date (tactical);
- add a crop whose sensitive stage falls outside the window, such as a small grain harvested in July (strategic);
- build soil water-holding capacity slowly through cover and residue (strategic, over years).

---

## 6. Core variables

| Variable | Plain-language meaning | Farmer question |
|---|---|---|
| Crop sequence | What was grown each season | What has this field been doing? |
| NDVI/EVI trajectory | Greenness through each season | When did the crop grow, and how strongly? |
| Living-cover / no-living-cover days | How much of the year the soil had green cover | How exposed is my soil? |
| Precipitation | Rain and snow received | Is enough water arriving, and when? |
| Root-zone soil moisture | Water available to roots (regional) | Was water short when the crop needed it? |
| Temperature and GDD | Heat accumulation and extremes | How fast did the crop develop, and was it heat-stressed? |
| Soil properties | AWC, drainage, organic matter, slope | What does my soil allow, and what does it need? |
| Anomaly | Difference from the location's own baseline | Is this unusual for here and this time of year? |
| Trend | Direction of change over years | Is this getting more frequent? |

### Why anomalies and baselines matter (kept)

`Anomaly = current condition - expected condition`

Say "root-zone soil moisture was in the driest fifth of years for this location in mid-July", not "soil moisture was 18%".

**New rule: baselines must be crop-specific.** Corn and soybean produce different greenness curves. A corn–soybean field compared with its all-years median will appear "anomalous" every year. Compare corn seasons with this field's corn seasons, and soybean with soybean.

---

## 7. Estimating crop stage

### 7.1 Key conclusion (kept)

Don't infer the growth stage from a single NDVI/EVI value. Infer an **estimated stage** from:

`crop type + planting date or calendar + NDVI/EVI trajectory + accumulated temperature + supporting water conditions`

Looking back makes this easier than v1's in-season problem. With the whole season in hand, fit the full curve (green-up, peak, decline) with a smoothing spline or a double-logistic fit. That is far more robust than estimating the stage mid-season from partial data.

### 7.2 Expected trajectory (kept)

| Stage | Typical NDVI/EVI behaviour | Interpretation |
|---|---|---|
| Pre-planting / bare soil | Low and stable | Little green vegetation |
| Emergence | Low but beginning to rise | Seedlings appearing |
| Vegetative growth | Rising fast | Canopy expanding |
| Full canopy / mid-season | High, flattening or peaking | Maximum green biomass |
| Senescence / maturity | Declining | Natural loss of greenness |
| Post-harvest | Sharp fall or sustained low | Crop removed; soil bare or covered by residue |
| Off-season green-up | Rising between harvest and next planting | Cover crop, weeds or volunteer plants; confirm with the farmer |

Low NDVI is ambiguous (unplanted, residue, snow, failure, data issues). The slope over 30–60 days tells you more than a single value.

### 7.3 Crop calendars

A crop calendar tells you where the crop **should** be; the satellite time series suggests where it **appears** to be. For the US, use NASS Crop Progress (weekly, by state). Elsewhere, use regional crop calendars such as GEOGLAM or FAO GIEWS.

### 7.4 Growing degree days, corrected

v1's formula had no upper cap. For maize, use the standard 86/50 °F method, which in Celsius is:

```text
T_max_adj = min(T_max, 30 °C)
T_min_adj = max(T_min, 10 °C)
T_max_adj = max(T_max_adj, 10 °C)        # if the whole day is below base, GDD = 0
GDD_day   = ((T_max_adj + T_min_adj) / 2) - 10 °C
GDD_cum   = sum(GDD_day since planting or estimated emergence)
```

Purdue Extension cites roughly **1,400 GDD to silking** and **2,700 GDD to black layer** (physiological maturity). These figures are in **°F-based units**; divide by 1.8 for °C-based units, giving about 780 and 1,500. Both depend on the hybrid's relative maturity ([Purdue NCH-40](https://www.extension.purdue.edu/extmedia/nch/nch-40.html)).

**Why the cap matters here:** the adaptation story is about hotter seasons. Without the cap, GDD overstates how far the crop should have developed, so normal growth looks like it is lagging. That produces false "lagging" findings in exactly the seasons the demo is about.

**Soybean:** its development is driven mostly by day length, so GDD predicts it poorly. Rely more on the NDVI trajectory and the calendar.

---

## 8. Engines

The pipeline has three deterministic engines and an optional explanation layer. Each engine writes to a shared **evidence JSON**, where every number carries its source dataset and date.

### 8.1 Engine 1: Field History

**Purpose:** reconstruct, season by season, what was grown, when it grew, and how much of the year the soil had living cover.

**Inputs:**

- field polygon;
- HLS surface reflectance with the Fmask quality layer, 2016–2025. L30 goes back to April 2013 if a longer record is needed;
- crop label per season from CDL (in the US), or entered by the farmer (the farmer's entry takes precedence).

**Processing:**

1. Mask clouds, cloud shadow, snow and water using Fmask.
2. Buffer the polygon inward by one pixel (30 m) so that edge pixels don't mix in roads or neighbouring fields.
3. Aggregate the valid interior pixels to a per-date median. Drop dates below the minimum pixel count (§15, V1).
4. Smooth each season's curve and extract the phenometrics: green-up, peak date and value, decline, and the post-harvest minimum.
5. Compute **living-cover days** (smoothed NDVI above a cover threshold) and **no-living-cover days** for each harvest-to-harvest year. Don't call these "bare-soil days": residue and snow also cover soil (§3.4).
6. Flag **spring green cover** when a green signal appears between 1 March and the cash crop's green-up. Cereal rye is mostly visible from mid-March to April, before termination. Don't rely on November–February: in Iowa, snow masking and low sun angles leave few valid scenes. Record an autumn green signal after harvest, but don't credit it as cover on its own.
7. Stretch goal: compute the residue proxy (NDTI/NBR2) on dry, non-green dates.

**Outputs per season:**

- crop, with its source and confidence;
- green-up, peak and decline dates;
- peak and integrated NDVI/EVI;
- living-cover days and no-living-cover days;
- spring-cover flag;
- number of valid observations, and a quality flag.

### 8.2 Engine 2: Stress Recurrence

**Purpose:** for each past season, determine whether development lagged and whether water or heat stress coincided with the crop's sensitive stage. Then summarise how often that recurs.

**Inputs:**

- Engine 1 outputs;
- daily maximum and minimum temperature and precipitation (NASA POWER, 1981 onward);
- root-zone soil moisture (SMAP L4, 2015 onward);
- a table of sensitive stages for each crop.

**Processing:**

1. Estimate stage dates. For corn, use capped GDD from green-up, cross-checked against the NDVI peak. For soybean, use the trajectory and the calendar.
2. Compute anomalies against the location's own climatology for the same day of year, as percentiles. Use POWER's long record for temperature and rainfall trends. SMAP's 2015–2025 record is too short on its own to support trend claims.
3. Flag a **stress-window season** using provisional rules for the team to agree. For example: root-zone soil moisture below the 20th percentile on at least 7 of the 14 days centred on estimated silking, **or** maximum temperature above the 80th percentile on at least 5 of those days.
4. Compute **relative vigour**: the season's peak and integrated NDVI compared with this field's median for the same crop.
5. Summarise recurrence, for example "stress-window seasons: k of n corn seasons", along with any trend across the decade.

**Outputs:**

- stress flags for each season, with the drivers that triggered them;
- relative vigour;
- a recurrence summary;
- confidence. This is capped at "moderate" whenever the drivers are regional (9 km or 0.5°).

### 8.3 Engine 3: Rotation Comparison

**Purpose:** compare 2–4 candidate rotations against the farmer's priorities, using the field's evidence, its soil and the crops' characteristics.

**Inputs:**

- Engine 1 and 2 summaries;
- soil: SSURGO available water capacity, drainage class, organic matter and slope class. Values from the farmer's own soil tests take precedence. Outside the US, use SoilGrids;
- crop-characteristics catalogue, sourced from extension guidance. For each crop: timing of the sensitive stage, seasonal pattern of water use, nitrogen fixation, residue amount and potential for winter cover;
- farmer priorities, ranked: soil protection, water and stress risk, nitrogen and input needs, workload and simplicity, crop diversity;
- farmer constraints, for example no market for small grains, no equipment for forage, or rented land.

**Processing:** transparent rules, no optimiser.

1. Drop any candidate that breaks a hard constraint the farmer stated.
2. For each remaining candidate and each criterion, give an **ordinal rating relative to the current rotation**: better, similar or worse. Each rating cites its evidence and states its confidence.
   - **Soil cover and living roots:** observed no-living-cover days, adjusted by the candidate's practice. For example, a cover crop fills the window from harvest to planting.
   - **Erosion protection:** cover rating combined with slope class.
   - **Water and stress exposure:** does the sensitive stage of each crop in the rotation overlap this field's recurring stress window, and how often?
   - **Nitrogen needs:** legume credits in the sequence.
   - **Crop diversity:** number of distinct crops and functional groups.
   - **Workload and complexity:** qualitative, using equipment and practices the farmer has confirmed.
3. Sort the candidates by the farmer's priority order. Show **what changes if the priorities change**, so the farmer can see how stable the ranking is.

Ratings are ordinal, not numeric scores, to avoid false precision. Judges scoring Validity will look for exactly this kind of restraint.

**Outputs:**

- a trade-off table;
- the evidence behind each cell;
- confidence;
- what to verify with an agronomist;
- what the tool cannot establish.

Income is either left out or entered by the farmer, never predicted.

### 8.4 Explanation layer (optional LLM)

- **Input:** the evidence JSON only.
- **Output:** a plain-language summary and the one-page brief for the farmer and adviser.
- **Rule:** every number and claim in the text must exist in the evidence JSON. This is enforced by an automated test (§15, V8).
- **Not permitted:** new thresholds, diagnoses, causal claims or recommendations.

---

## 9. Reading the evidence (sensor-fusion scenarios, looking back)

**Scenario A: recurring water stress at silking.** In k of n corn seasons, root-zone moisture was in the driest fifth around estimated silking and maximum temperatures were above normal. In those seasons, corn peak greenness was below this field's corn median.

> Evidence is consistent with recurring mid-season water stress for corn on this field. Rotations that reduce how often corn is grown, or shift sensitive stages away from midsummer, lower the exposure. Confidence: moderate, because the drivers are regional.

**Scenario B: deficit buffered.** Regional soil moisture was dry, but field greenness tracked this field's own median for the crop.

> The regional deficit did not show up in the crop's development. The soil's water-holding capacity, local rain or irrigation may have buffered it. Do not attribute stress to this field, and give lower weight to water-driven rotation change.

**Scenario C: vigour decline with no environmental explanation.** Rainfall, moisture and temperature were all near normal, but vigour was below the field's median.

> The cause is uncertain. Candidates include pest or disease pressure, nutrient supply, drainage or ponding, management changes and data artefacts. A field check is recommended. Rotation can break pest cycles, but the tool does not diagnose.

**Scenario D (new): long periods without living cover.** Every year, the field shows no living cover from harvest to late-spring green-up; on a corn–soybean field without a cover crop this can be around seven months.

> The largest observed soil-health gap is cover. Cover-crop options rate better on soil protection. Check the slope class for erosion exposure.

**Scenario E (new): spring green detected.**

> This is consistent with a cover crop, but weeds or volunteer plants look the same. Ask the farmer to confirm before crediting it.

> **Resolution caveat.** Vegetation evidence is field-scale (30 m). The drivers are regional: SMAP root-zone moisture at 9 km, POWER weather at about 0.5°. A single SMAP cell can contain many fields with different soils and drainage. Present the drivers as regional context for the field's own signal, never as measurements of the field.

---

## 10. Data sources

| Dataset | Provider | What it gives | Resolution | Period | Role |
|---|---|---|---|---|---|
| **HLS L30/S30 v2.0** surface reflectance + Fmask | NASA LP DAAC | Compute NDVI, EVI, NDTI; quality mask | 30 m; combined revisit every 2–3 days nominally | Landsat 8 from Apr 2013; Sentinel-2A from Nov 2015 (2B 2017, 2C 2025; Landsat 9 2021) | **Core:** field history |
| **HLS VI v2.0** (HLSL30_VI, HLSS30_VI) | NASA LP DAAC | Nine precomputed indices incl. NDVI, EVI, NBR2 | 30 m | Forward-processed from Dec 2024; archive back-processed | Convenience. **Coverage confirmed 9 Nov for tile T15TVG, 2016–2025** (VI vs SR granules: L30 515/516, S30 958/962). Check again for any other tile |
| **MSLSP30NA (MuSLI) v1.1** | NASA LP DAAC | Yearly phenology dates from HLS (green-up, peak, decline, amplitude) | 30 m, North America | 2016–2019 (confirmed from CMR metadata, 9 Nov) | **Validation** of Engine 1. Not offered in AppEEARS; download via Earthdata |
| **SMAP L4** (SPL4SMGP) | NASA GMAO / NSIDC | Surface and root-zone soil moisture, 3-hourly | 9 km | Mar 2015 – present | Root-zone moisture anomaly (regional) |
| **NASA POWER** | NASA LaRC | Daily max/min temperature, precipitation, solar radiation | ~0.5° | 1981 – present | GDD, heat and rainfall anomalies and trends (regional) |
| **GPM IMERG** | NASA | Precipitation | 0.1° | 2000 – present | Optional finer rainfall |
| **NEX-GDDP-CMIP6** | NASA | Downscaled daily climate projections | 0.25° | 1950–2100 | Stretch: forward-looking panel |
| MOD13Q1 | NASA | 16-day NDVI/EVI | 250 m | 2000 – present | Fallback or longer baseline; too coarse for small fields |
| Cropland Data Layer (CDL) | USDA NASS | Crop type each year | 30 m | National from 2008; 2025 released | Crop sequence and ground truth (US) |
| Crop Progress | USDA NASS | Weekly % of crop at each stage, by state | State | Weekly in season (2026 reports published) | Validation of stage estimates |
| SSURGO / gSSURGO | USDA NRCS | AWC, drainage class, organic matter, slope | Survey map units | — | Soil information (US) |
| SoilGrids 2.0 | ISRIC | Modelled soil properties with uncertainty | 250 m | — | Soil information outside the US |
| OpTIS | CTIC / TNC / Regrow | Tillage and cover-crop adoption | Aggregated: district, HUC8 watershed, state | 2005–2019 | Context only; not field-level |

**Access:**

- **AppEEARS:** use it for HLS and SMAP area extractions. It keeps NASA provenance visible for the Space Agency Data field, and HLS VI was added to it in December 2025 ([Earthdata notice](https://www.earthdata.nasa.gov/data/alerts-outages/hls-vegetation-indices-products-available-appeears)).
- **NASA POWER API:** weather. No login needed.
- **CropScape:** CDL.
- **Soil Data Access / Web Soil Survey:** SSURGO.
- **Google Earth Engine:** faster if the geospatial lead already knows it. Still cite the NASA collections explicitly.

---

## 11. Spatial and temporal resolution

### 11.1 Spatial (kept, with a field-size rule)

A 30 m pixel covers 900 m², about 0.09 ha. A 40-acre (16 ha) field holds roughly 180 pixels before the inward buffer, and fewer after it. For every field, ask:

- How many valid interior pixels remain after buffering and masking?
- Are edge pixels contaminating the result?
- Does the field boundary change across years, for example when a field is split or merged?
- Is the tool making sub-field claims the data cannot support? (For the MVP it should make none.)

The drivers are coarser than the field by two to four orders of magnitude in area (§9 caveat).

### 11.2 Temporal (kept, reframed)

A nominal revisit is not the same as a usable observation. Clouds, haze and quality filtering create gaps. Separate:

- nominal revisit frequency;
- valid clear-sky observation frequency;
- analysis frequency (here: once per season).

Looking back is more forgiving than monitoring live, because a whole-season fit can bridge gaps. Cloudy springs still blur the green-up date. Record the number of valid observations for each season and lower the confidence when it is low; don't drop seasons silently.

---

## 12. Product and responsible-AI principles

### 12.1 Analytical core

Earth-observation, soil and calendar data → quality control → per-season time series → field history → stress recurrence → rotation comparison.

### 12.2 Appropriate LLM role (kept)

The LLM may explain indicators, synthesise evidence that has already been computed, translate, and support exploration. It may not invent measurements, thresholds, diagnoses, causal claims or ratings.

### 12.3 Human oversight

A rotation choice affects income, soil and leases for years. The tool frames the conversation between the farmer and their agronomist or extension adviser. It does not make the decision. The one-page summary exists to support that conversation.

### 12.4 Explainability

Every rating in the trade-off table should show:

- the evidence behind it (dataset, seasons and dates);
- the baseline it is compared against;
- its confidence, and why;
- what is missing;
- what to verify in the field or with an agronomist.

### 12.5 Users with low data literacy

Use "better / similar / worse for your priority", not scores. Put numbers in context ("about seven months a year without living cover"), not as raw index values. The one-page summary should make sense to someone who never opens the map.

---

## 13. Hackathon MVP

### 13.1 Primary user flow

1. The farmer selects a field on the map; demo fields are preloaded.
2. The farmer confirms or edits the crop history (prefilled from CDL) and soil information (prefilled from SSURGO).
3. The farmer ranks their priorities and states any constraints.
4. **Field History view:** a strip of ten seasons showing the crop, bars for living cover and no living cover, and stress flags.
5. **Changing Conditions view:** trends in season heat, rainfall and root-zone moisture during the sensitive window.
6. **Rotation Options view:** 3 candidates × criteria, with evidence on click, confidence, and what changes if the priorities change.
7. A one-page summary for an agronomist conversation, to export.

### 13.2 Scope

| In | Stretch | Out |
|---|---|---|
| 1–3 precomputed Iowa fields, 2016–2025 | Draw any Iowa field (live extraction) | Yield or profit forecasts |
| CDL crop sequence; HLS NDVI/EVI; POWER; SMAP L4; SSURGO | Residue proxy (NDTI/NBR2) | Soil chemistry from space |
| Three candidate rotations; rule-based comparison | NEX-GDDP-CMIP6 projection panel | In-season alerts |
| Validation chart (§15) | LLM summary; a second region for transferability | ML crop classification |

### 13.3 Minimum output

```text
ILLUSTRATIVE ONLY: bracketed values are placeholders, not computed results

Field: [demo field], [county], Iowa  (~[n] ha, [n] valid interior pixels)
Seasons analysed: 2016–2025 (10)      Current rotation: corn–soybean

What this field has done
- Crop sequence (CDL): C S C S C S C S C S
- Soil without living cover: about [x] months a year, mostly late Oct to late May
- Spring green cover detected: [0] of [9] springs

Recurring stress
- Root-zone moisture was in the driest fifth around estimated silking
  in [k] of [5] corn seasons
- In those seasons, corn peak greenness was below this field's corn median
- Confidence: moderate (soil moisture is regional at 9 km; greenness is field-scale at 30 m)

Your priorities: 1 soil protection   2 water risk   3 workload

Option                          Soil cover   Water risk   Workload   Confidence
Corn–soybean (current)          baseline     baseline     baseline   —
Corn–soybean + cereal rye       better       similar      worse      moderate
Corn–soybean–oats/clover        better       better       worse      low–moderate

Worth considering: the cover-crop option addresses the largest observed gap
(no living cover) with the smallest change to operations.
Verify with an agronomist: cereal rye ahead of corn (termination timing);
a local market for oats.
Not established by this tool: yield or profit effects on this field; change in soil carbon.
```

---

## 14. Technical architecture

```text
Field polygon + farmer inputs (priorities, constraints, soil tests, history edits)
                              |
                              v
NASA EO: HLS (+Fmask), SMAP L4, POWER, [NEX-GDDP-CMIP6]
USDA ancillary: CDL, SSURGO, Crop Progress (validation)
                              |
                              v
Quality control: Fmask, one-pixel inward buffer, minimum valid pixels
                              |
                              v
Per-season time series: smoothing, phenometrics, cover days,
anomalies vs local climatology (crop-specific baselines)
                              |
               +--------------+--------------+
               v                             v
      Engine 1: Field History      Engine 2: Stress Recurrence
               +--------------+--------------+
                              v
             Engine 3: Rotation Comparison  <-- crop catalogue,
                              |                 soil, priorities
                              v
        Evidence JSON (every number traceable to dataset + date)
                              |
                              v
  UI: season strip | trend panel | trade-off table | one-page summary
  (optional) LLM explanation constrained to the evidence JSON
```

### Build approach for 48 hours

Precompute the demo fields offline, in a notebook that writes Parquet or JSON. The app reads the precomputed evidence, so the demo never depends on a live API call. Live extraction for any field is a stretch goal.

### Processing steps

1. Validate the field geometry and apply the inward buffer; check the pixel count (V1).
2. Pull HLS surface reflectance and Fmask for 2016–2025; or pull HLS VI if the coverage check passed.
3. Mask, aggregate the interior pixels to per-date medians, and record the valid counts (V2).
4. Attach the CDL crop label to each season.
5. Smooth each season and extract the phenometrics (V3 against MSLSP30NA).
6. Compute living-cover days, no-living-cover days and the spring-cover flag (V6).
7. Pull POWER daily weather. Compute capped GDD (V10) and estimated stage dates (V4 against Crop Progress).
8. Pull SMAP L4 root-zone moisture and compute day-of-year percentiles.
9. Apply the stress-window rules; compute relative vigour within each crop and recurrence.
10. Load the soil, the crop catalogue, the priorities and the constraints; run Engine 3 (V7, V9).
11. Write the evidence JSON. Render the UI and the summary (V8).

---

## 15. Validation plan and acceptance criteria

These are **proposed targets for the team to agree**, not established thresholds. Each can be tested within the hackathon. If a target is missed, report it in the demo as a finding. That is evidence of Validity, not a failure.

| ID | Component | Test | Pass criterion |
|---|---|---|---|
| V1 | Field geometry | Valid interior pixels for each date used, after the buffer and Fmask | ≥ 50 pixels; dates below this are dropped and counted |
| V2 | Observation density | Valid dates from April to October in each season | ≥ 8; seasons below this are flagged low confidence, not dropped |
| V3 | Phenology | Engine 1 green-up (50% greenness increase) compared with the MSLSP30NA 50PCGI layer (median over the field's pixels), 2016–2019 | Within ±10 days in ≥ 80% of field-seasons. With 1–3 fields and four years this is only 4–12 field-seasons: report n and present the result as a sanity check |
| V4 | Stage timing | Estimated corn silking date compared with Iowa NASS Crop Progress | Falls between the dates Iowa reached 25% and 75% silked in ≥ 70% of corn seasons |
| V5 | Crop sequence | Only if the crop is inferred from phenology: agreement with CDL where the CDL majority class covers ≥ 80% of the field's pixels | ≥ 90% agreement. If CDL is used directly, state that and skip this test |
| V6 | Cover classification | 10 randomly sampled off-season dates per field: green / not-green call compared with a visual check of the HLS true-colour image | ≥ 9 of 10 match |
| V7 | Determinism | The same inputs run twice | Identical evidence JSON (hash match) |
| V8 | Traceability | Every number in the UI and the LLM text is looked up in the evidence JSON | 100%; the build fails otherwise |
| V9 | Priority sensitivity | Change the priority order | The ranking may change; no evidence value or rating changes |
| V10 | GDD unit tests | (Tmax 35, Tmin 18) → 14.0; (25, 5) → 7.5; (8, 2) → 0.0 GDD in °C | All pass |

The V4 comparison sets one field against a state-wide distribution, so treat it as a sanity check, not as accuracy.

---

## 16. Assumptions, validation gaps and failure modes

### 16.1 Assumptions for the MVP

- The demo fields are large enough to keep useful interior pixels after buffering.
- CDL labels corn and soybean on the demo fields reliably. Check the confidence layer where it is available.
- SSURGO represents the field reasonably. Soil can vary within a field, and the MVP does not model that variation.
- The crop catalogue values come from extension sources, and each one has a reference.
- The farmer's stated priorities and constraints are taken as given.

### 16.2 Must be validated

- The NDVI threshold for "green cover" and the stress-window rules.
- Sensitive-stage windows for each crop and hybrid maturity.
- The rating rules in Engine 3, with an agronomist or extension specialist.
- Whether farmers find the season strip and trade-off table understandable and useful.

### 16.3 Likely failure modes

- Cloudy springs blurring green-up dates.
- Residue or snow read as bare soil; weeds or volunteer corn read as a cover crop.
- Field boundaries that change across years; CDL errors at field edges.
- Too few seasons per crop for a crop-specific baseline (about five corn seasons in ten years). Report n next to every crop-specific comparison.
- One 9 km SMAP cell covering fields with different soils and drainage. Tile drainage complicates moisture behaviour.
- SMAP's short record (2015 onward) mistaken for a climate trend.
- Recommendations that can't be acted on: no market for small grains, no equipment, or lease terms that discourage long-term investment.
- Harvest misread as crop failure, or stress misread as senescence (from v1).

---

## 17. Suggested team roles

- **Product/solution lead:** the user and the decision, scope, the rules check on 13 November, the pitch and integration.
- **Geospatial/remote-sensing lead:** HLS and SMAP extraction, Fmask, phenometrics, validation tests V1–V6.
- **Engineer:** the evidence JSON, the UI, deployment, tests V7–V10.
- **UX/storytelling lead:** the season strip, the trade-off table, the one-page summary, the 30-second video and 7 slides.

Two judgement calls:

- A geospatial lead still adds more than a second general-purpose AI developer.
- **30 minutes with an agronomist or extension specialist** over the weekend, to sanity-check the candidate rotations and rating rules, is worth more than another developer.

---

## 18. Pre-event preparation (T-8 to T-0)

If the 2026 rules restrict work before the event, keep this period to learning, account setup and checking data access.

### 18.1 Two-hour learning plan

- **0:00–0:25 Soil health and rotation.** The four NRCS principles; what rotation changes; the corn–soybean system; cereal rye as a cover crop; the diversification evidence (Bowles et al. 2020).
- **0:25–0:50 Remote sensing.** Bands, pixels, resolution, NDVI/EVI, Fmask; the SWIR residue index; detecting winter cover (Seifert et al. 2018).
- **0:50–1:15 NASA data.** HLS, SMAP L4, POWER, MSLSP30NA. For each: what is observed and what is modelled, resolution, period, limits.
- **1:15–1:35 Climate adaptation.** `hazard → exposure → vulnerability → impact → adaptation`, worked through the rotation example in §5.2.
- **1:35–2:00 Worked case.** For a central Iowa corn–soybean field, answer:
  - What has the field done over ten seasons?
  - When is its soil without living cover?
  - Does stress recur at silking?
  - What is changing?
  - Which rotation options address the field's largest gap, and at what cost?
  - What can satellite data not establish?

### 18.2 Setup checklist

- [ ] Confirm the challenge text and the **Resources** tab on the challenge page (Resources published 13 Nov; not retrievable by automated fetch on 13 Nov, so read it manually). Plan to use or cite every NASA dataset listed there.
- [ ] Read the 2026 Project Submission and Judging & Awards guides (13 Nov). Pre-work rule confirmed from the 2026 FAQ (§1.4); demo format, data field and criteria still to confirm.
- [ ] Ask the Local Lead in writing whether the pre-event material in this repo is acceptable (§1.4).
- [ ] Earthdata Login and AppEEARS access working for every team member who needs them.
- [x] Check HLS VI coverage for 2016–2025 on the chosen MGRS tile. Done 9 Nov: complete on T15TVG, so use HLS VI.
- [ ] Agree the region and the decision (§3.2).
- [ ] Line up an agronomist or extension contact for the weekend.

---

## 19. Demo narrative

### 19.1 Global submission (2022 format: 30-second video or 7 slides; confirm for 2026)

**Seven slides:**

1. The farmer and the decision.
2. Ten seasons on one strip.
3. The soil-cover gap.
4. Recurring stress and changing conditions.
5. Rotation trade-offs against the farmer's priorities.
6. How we know: validation and limits.
7. NASA data used, and how it transfers to other regions.

**30-second script:**

- 0–5 s: a farmer planning next year's rotation.
- 5–12 s: what the field has done, from NASA's 30 m data.
- 12–20 s: no living cover [x] months a year; dry spells at silking in [k] of [n] corn years (fill in from computed results).
- 20–27 s: three rotations compared against the farmer's priorities.
- 27–30 s: the NASA datasets used and what the tool doesn't claim.

### 19.2 Local three-minute pitch

- **0:00–0:20** It's November. A central Iowa farmer is planning next year's rotation.
- **0:20–0:50** The field's history: ten seasons on one strip, showing the crop and living cover.
- **0:50–1:30** What recurs and what is changing: stress at silking, heat trends, root-zone moisture, with the regional caveat stated.
- **1:30–2:15** Priorities in, options out. Change a priority live and show what changes and what doesn't.
- **2:15–2:40** How we know: validation against MSLSP30NA and NASS Crop Progress, and what satellites can't see.
- **2:40–3:00** It transfers: the same pipeline works outside the US with SoilGrids, local crop calendars and crop inference from phenology. Adaptation is a decision made every year, and the tool supports that decision rather than adding another dashboard.

---

## 20. Key principles to remember

- A rotation is a decision that spans several years; build for that horizon.
- The field's own history is the best baseline, and baselines must be crop-specific: compare corn with corn.
- Satellites can see cover, timing and vigour. They cannot see soil carbon or nitrogen.
- Low off-season NDVI is not proof of bare soil, and high off-season NDVI is not proof of a cover crop.
- Regional drivers are context, not field measurements.
- Cap GDD; for maize, bound temperatures to 10–30 °C.
- Rainfall is not the same as water available to the plant (kept).
- Multiple independent signals are stronger than one indicator (kept).
- Show trade-offs; don't name an optimum.
- Every number must trace to a dataset and a date.
- Published rotation effects are context, not forecasts for this field.
- The goal is a better decision conversation, not a prediction.

---

## 21. Future work: in-season monitoring and alerting (from v1 §10)

This is deferred because it serves the operational horizon and the brief is strategic. It is still worth one slide, because the same engines run during the season would build next year's rotation evidence.

- **State machine:** `NORMAL → WATCH → WARNING → CRITICAL → RECOVERING → NORMAL`. Notify mainly on state transitions.
- **Cadence:** event-driven alerts plus a weekly digest, with more sensitive checks during critical stages. Suppress repeated alerts while nothing changes. Alert again on material worsening.
- **Timeliness:** `alert latency < useful intervention window`.
- **Conceptual priority:** `severity × stage sensitivity × persistence × confidence × actionability`. This is not a validated formula; it needs local agronomic calibration.
- **Principle:** data refresh frequency should not set alert frequency. Notify only when the farmer's decision should change.

---

## 22. Links

### Challenge and rules

- [Field Shift: Adapting Farms with NASA Data](https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=details)
- [Space Apps 2026: dates and submission window](https://www.spaceappschallenge.org/2026/)
- [Participant FAQs (2026)](https://www.spaceappschallenge.org/resources/participant-faqs/)
- [Judging & Awards Guide (2024 criteria)](https://spaceappschallenge.org/resources/judging-awards-guide)
- [2022 Project Submission Guide (demo format precedent)](https://spaceapps-prod.s3.amazonaws.com/media/documents/Space_Apps_2022_Project_Submission_Guide.pdf)
- [Legacy FAQ (pre-work rule precedent)](https://legacy.spaceappschallenge.org/resources/faq/)

### NASA data

- [HLS data: product start dates, latency, VI back-processing status](https://hls.gsfc.nasa.gov/hls-data)
- [HLS vegetation-index products announcement](https://www.earthdata.nasa.gov/news/harmonized-landsat-sentinel-2-project-releases-vegetation-indices)
- [HLS L30 VI v2.0 catalogue entry](https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlsl30-vi-2.0)
- [HLS S30 VI v2.0 catalogue entry](https://www.earthdata.nasa.gov/data/catalog/lpcloud-hlss30-vi-2.0)
- [HLS VI in AppEEARS (Dec 2025)](https://www.earthdata.nasa.gov/data/alerts-outages/hls-vegetation-indices-products-available-appeears)
- [MSLSP30NA v011 (MuSLI 30 m phenology)](https://www.earthdata.nasa.gov/data/catalog/lpcloud-mslsp30na-011)
- [SMAP L4 surface and root-zone soil moisture](https://nsidc.org/data/spl4smgp)
- [NASA POWER](https://power.larc.nasa.gov/)
- [AppEEARS](https://appeears.earthdatacloud.nasa.gov/)
- [NASA Earthdata Search](https://search.earthdata.nasa.gov/)
- [NASA Science: HLS Vegetation Indices explainer](https://science.nasa.gov/mission/landsat/hls-vegetation-indices/)
- [NASA Science: Measuring Vegetation (NDVI & EVI)](https://science.nasa.gov/earth/earth-observatory/measuring-vegetation-ndvi-evi/)
- [NASA MODIS Vegetation Index Products](https://modis.gsfc.nasa.gov/data/dataprod/mod13.php)
- [NASA/USDA Global Agricultural Monitoring (GLAM)](https://glam1.gsfc.nasa.gov/)

### Ancillary data

- [CropScape (Cropland Data Layer)](https://nassgeodata.gmu.edu/CropScape/)
- [CDL in Google Earth Engine (band and year availability)](https://developers.google.com/earth-engine/datasets/catalog/USDA_NASS_CDL)
- [SoilGrids](https://soilgrids.org/)
- [OpTIS 2.0 coverage and method (Farm Progress)](https://www.farmprogress.com/crops/optis-20-adds-geography-cropping-seasons-and-search-options)

### Research and agronomy

- [Bowles et al. 2020, *One Earth*: rotation diversification and resilience](https://par.nsf.gov/servlets/purl/10331499) (DOI: 10.1016/j.oneear.2020.02.007)
- [Seifert, Azzari & Lobell 2018, *ERL*: satellite detection of cover crops](https://fse.fsi.stanford.edu/node/28583)
- [Purdue NCH-40: corn growing degree days](https://www.extension.purdue.edu/extmedia/nch/nch-40.html)

### Other teams on this challenge (competitive context)

- [FieldShift-NASA](https://github.com/sagar25446-prog/FieldShift-NASA) · [farmstack](https://github.com/anirban-islam/farmstack) · [AgroScope](https://github.com/Zahin-Tajwar/AgroScope)

---

## 23. Immediate next steps

**Friday 13 November (preparation only; the 2026 FAQ bars work on the challenge before the event):**

1. Read the challenge Details and Resources tabs and the 2026 guides manually; fill in `docs/rules_check_2026.md`. Add any Resources-tab NASA datasets to §10 and `REFERENCES.md`.
2. Message the Local Lead about the pre-event material in this repo (§1.4) and keep the reply.
3. Agree the region and the decision; Iowa corn–soybean is recommended (§3.2).
4. Every team member: Earthdata login working (`python prep/check_access.py`). HLS VI coverage is already confirmed for T15TVG.
5. Line up an agronomist or extension contact.

**Saturday 14 November:**

5. Fix 1–3 demo fields. Extract HLS for 2016–2025 with Fmask, plus CDL and SSURGO.
6. Build Engine 1: phenometrics and cover days. Run V1–V3 and V6.
7. Pull POWER and SMAP L4. Compute capped GDD and build Engine 2. Run V4 and V10.

**Sunday 15 November:**

8. Build the crop catalogue and three candidate rotations, then Engine 3. Run V7–V9.
9. Build the UI: season strip, trend panel, trade-off table, one-page summary.
10. Make the validation chart and the limits slide; cut the 30-second video and 7 slides. Submit before 11:59 pm local time, with the Space Agency Data and References fields complete.
