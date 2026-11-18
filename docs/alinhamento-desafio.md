# NASA Space Apps 2026 challenge alignment

This document maps each requirement in the *“Turning the Tables on Farming: Adapting Farms with NASA Data”* challenge to the corresponding GeoSafra feature. It also identifies remaining work so the team can present the project accurately.

Status key. ✅ Complete · 🟡 Partial · ⏭️ Planned

## Core objective

| Requirement | Status | Where to find it |
|---|---|---|
| A decision-support tool that combines NASA observations with local soil data, crop characteristics, and grower priorities | ✅ | The field form (`Fields/Form.vue`) captures soil, crop history, priorities, and constraints. The engine is in `geo-service/app/engine/`. |
| Explore rotations that improve soil health and resilience to climate and water stress | ✅ | The **Compare** tab uses 10 criteria ([rotation engine](motor.md)). |
| Compare **at least three strategies, including the current rotation** | ✅ | Strategy A is the current rotation. Up to three alternatives are selected using a Jaccard similarity rule to preserve diversity. |
| For every strategy, explain **why** it was suggested and show **evidence**, **benefits**, **information gaps**, and **risks to review locally** | ✅ | `StrategyCard.vue` uses `rationale`, `evidences` (with dataset and period), `benefits`, `information_gaps`, `local_review_risks`, and `conflicts`. |
| Support grower judgment | ✅ | Every analysis displays a disclaimer. Account registration includes an acknowledgment. The tool also provides a “Where your judgment matters most” section, a low-confidence badge, and “Makes sense” and “Needs adjustment” feedback. |

## NASA data

| Dataset | Status | Use |
|---|---|---|
| **NASA POWER** (daily, 2005–2025) | ✅ | Temperature, precipitation, humidity, wind, radiation, pressure, and soil moisture (GWETROOT/GWETTOP) support FAO-56 ETo, water balance, dry spell, frost, heat, extreme rainfall, and trend calculations. |
| **SRTM** (elevation, ~30 m) | ✅ | Field slope, Embrapa terrain class, and the RUSLE LS factor for erosion risk (`geo-service/app/terrain/`). |
| **MODIS** (NDVI MOD13Q1/MYD13Q1 v061, 250 m, 16-day composites, past 5 years) | ✅ | Monthly vegetation cover (P10/P50/P90), low-greenness months compared with bare soil from crop history, and recent imagery compared with typical conditions and trends (`geo-service/app/vegetation/`). Reads NASA LP DAAC data through its public Microsoft Planetary Computer mirror. This dataset informs diagnosis, evidence, and information gaps. Strategy scores are independent of it. |
| **HLS** v2.0 (Landsat 8/9 + Sentinel-2, 30 m NDVI, past 2 years) | ✅ | Field-scale greenness per image, with cloud and shadow screening by Fmask. The calendar and diagnosis use HLS when it covers ≥ 10 months, with MODIS as the fallback. |
| **MODIS LST** (MOD11A2, land surface temperature, 1 km, 8-day composites, 3 years) | ✅ | The calendar highlights hot surfaces. It compares land surface temperature with maximum air temperature from POWER as a potential sign of bare soil or water stress. MODIS covers all months at 1 km and complements 70 m ECOSTRESS observations from cloud-free overpasses. |
| **MODIS ET/PET** (MOD16A3GF, 500 m, annual, 5 years) | ✅ | The ratio of actual to potential evapotranspiration describes observed water stress (low, moderate, or high) in the evidence for all strategies. |
| **SMAP** (SPL3SMP_E, 9 km soil moisture, 2 years) | ✅ | The “Dry soil” row shows conditions relative to the site’s typical soil moisture. The diagnosis also compares the latest month with typical conditions (`geo-service/app/earthdata/`, Earthdata Cloud OPeNDAP). |
| **ECOSTRESS** (ECO_L4T_ESI, 70 m, 2 years) | ✅ | The evidence includes the field-scale evaporative stress index for each cloud-free overpass. |
| **GRACE/GRACE-FO** (JPL RL06.3 v04 mascons, since 2002) | ✅ | Tracks total regional water storage and its trend using Sen’s slope and the Mann–Kendall test. Warns when water storage is declining. |
| **GPM IMERG** (monthly precipitation, 0.1°, since 2016) | ✅ | Compares satellite precipitation with POWER. The example shows 1,449 mm/year from GPM and 1,106 mm/year from POWER, which prompts a check against the farm’s rain gauge. It also compares the past 12 months with the long-term mean. The Earthdata account must accept the GES DISC EULA. |

## Conditions and data

| Requirement | Status | Where to find it |
|---|---|---|
| Relate temperature, soil moisture, rainfall, evaporation, and stress to crop vulnerability | ✅ | The vulnerability calendar and “When your current crop is most exposed.” |
| Explain scientific terms such as evapotranspiration, moisture anomaly, NDVI, frost, and water balance | ✅ | Question-mark icons throughout the interface open a glossary with more than 25 terms (`database/data/glossary.php`). |
| Explain how satellite observations differ from field measurements and how to combine them | ✅ | Section 2 of **How it works**. Confidence increases when growers provide soil test and market data. |

## Modeling and uncertainty

| Requirement | Status | Where to find it |
|---|---|---|
| Use statistics to describe historical patterns | ✅ | P10/P50/P90 percentiles, the Mann–Kendall test and Sen’s slope, and anomalies over the latest 3 years. |
| Highlight seasonal transitions, bare soil, and months of stress | ✅ | The monthly calendar ranks heat, frost, drought, heavy rainfall, bare soil (crop history), low greenness (HLS/MODIS), and hot surfaces (MODIS LST) at levels 0/1/2. Cards show NDVI and observed heat and water stress. |
| Explain how the model handles uncertainty and where local validation is needed | ✅ | Confidence by criterion and strategy, score ranges across dry and wet years, and documented information gaps. |
| Explain how the ranking can be audited | ✅ | README decision 5. The engine combines rules and multiple criteria, and every score is traceable to its data and rule. |
| Harmonize datasets at different resolutions on a common grid | 🟡 | The tool combines climate, terrain, and vegetation at the field level, using a POWER grid point (~50 km), a 30 m SRTM grid, 30 m HLS pixels, and MODIS pixels at 250 m, 500 m, and 1 km. Raster resampling is still pending. |

## Rotation strategies

| Requirement | Status | Where to find it |
|---|---|---|
| Cover nutrient cycling, erosion, organic matter, pests, water use, forage, and markets | ✅ | Nine adjustable criteria plus climate resilience. |
| Align options with grower priorities | ✅ | Set each criterion to 0–5 stars. The ranking updates when the weights change. |
| Explain nitrogen-fixing crops, cover crops, deep roots, and drought-tolerant crops | ✅ | Glossary keys `fixacao`, `cobertura`, `raiz`, and `tolerante_seca`, plus explanations for each criterion. |

## Maps and visualization

| Requirement | Status | Where to find it |
|---|---|---|
| Interactive field map | ✅ | `MapPicker.vue` (MapLibre and satellite imagery) supports boundary drawing and area calculation. |
| Field-level vulnerabilities such as erosion, water stress, and frost | 🟡 | The monthly calendar and **terrain** card show slope, terrain class, and the LS factor. Maps of zones within the field are still pending. |
| Timelines and scenario controls for rainfall and temperature | ✅ | Annual time-series charts and the **What if?** tab (rainfall −40% to +20%, temperature +0 to +3 °C). |

## Grower-centered design

| Requirement | Status | Where to find it |
|---|---|---|
| Accessible to people with limited technical experience | ✅ | Plain language, icons, and a mobile-first layout. Charts load after the summary to accommodate slow connections. |
| Capture priorities and constraints such as water, equipment, and markets | ✅ | Record irrigation (mm/day), unavailable equipment, excluded crops, and crops with or without known buyers. |
| Remind users that the tool supports grower judgment | ✅ | The footer, comparison, and account registration display a disclaimer. |
| Protect grower data | ✅ | Account sign-in restricts users to their own fields. Users can delete their fields at any time under Brazil’s LGPD. The public example is read-only. |
