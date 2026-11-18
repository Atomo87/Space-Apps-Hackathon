# B1 contract — Laravel ↔ geo-service

The base URL is `GEO_SERVICE_URL` (for example, `https://geosafra-geo-service.onrender.com`). Send the `X-GeoSafra-Token: <GEOSAFRA_TOKEN>` header when a token is configured.

Errors use `application/problem+json` (RFC 9457), with `detail` in Portuguese. FastAPI validation errors return HTTP 422 with a list in `detail`.

| Method | Route | Use | Typical time |
|---|---|---|---|
| GET | `/health` | Health check and keep-alive ping | < 1 s (up to ~60 s during a Render cold start) |
| GET | `/v1/catalog` | Crops, pests, equipment, and rotation templates | < 1 s |
| POST | `/v1/climate-profile` | Retrieve NASA POWER data and calculate indicators | 10–90 s uncached, < 1 s cached |
| POST | `/v1/terrain` | Use SRTM elevation to calculate slope and the LS factor | 1–5 s uncached, < 1 s cached |
| POST | `/v1/vegetation` | Field vegetation cover from 250 m MODIS NDVI and 30 m HLS | 20–60 s uncached, ~3 s cached |
| POST | `/v1/earthdata` | SMAP, GPM IMERG, ECOSTRESS, and GRACE-FO (requires `EARTHDATA_TOKEN`). Returns `{smap, gpm, ecostress, grace, notes}`. Any dataset may be `null`, with the reason in `notes`. | 40–90 s uncached, ~5 s cached |
| POST | `/v1/stress` | Observed land surface heat and water stress from MODIS LST and MODIS ET/PET | 5–30 s uncached, ~2 s cached |
| POST | `/v1/analysis` | Diagnosis and strategies A–D | < 1 s |

## POST /v1/vegetation

```json
{ "latitude": -18.9, "longitude": -48.55 }
```

1. Search STAC (`modis-13Q1-061` on the Microsoft Planetary Computer) for 16-day Terra (MOD13Q1) and Aqua (MYD13Q1) composites that cover the point over the last `NDVI_YEARS` years (default 5).
2. Read NDVI and reliability for the 250 m pixel in each composite (`/api/data/v1/item/point`, eight concurrent requests). Include only reliability ratings of 0 or 1 (cloud-free and snow-free).

| Field | Contents |
|---|---|
| `monthly[12]` | NDVI `p10`, `p50`, `p90`, the number `n` of valid images, and `level` 0/1/2 (low greenness at P50 < 0.40 and very low greenness below 0.30) |
| `low_green_months`, `peak`, `trough` | Low-greenness months, the greenest month, and the least green month |
| `recent` | Mean of the last three valid images, anomaly relative to the monthly median, and whether it fell below P10 |
| `trend` | Annual Sen’s slope and Mann–Kendall test of the annual mean, using years with ≥ 15 valid images |
| `series` | All valid observations (`date`, `ndvi`) for charting |
| `coverage`, `thresholds`, `dataset`, `citation`, `source_note`, `failed_requests` | Traceability information |

The `hls` field contains the same summary for **HLS v2.0** (HLSL30 and HLSS30). It uses 30 m NDVI from the last `HLS_YEARS` years and applies Fmask to exclude cloud, shadow, and water pixels. If imagery is unavailable, `hls` is `null` and the rest of the response is still returned.

## POST /v1/stress

Uses the same request body as `/v1/vegetation`. The response is `{ "lst": {...} | null, "et": {...} | null, "notes": [] }`. The two datasets are independent. The endpoint returns HTTP 502 if both fail.

| Field | Contents |
|---|---|
| `lst.monthly[12]` | Daytime land surface temperature (MOD11A2, ~10:30 a.m., 1 km). Includes `p50`, `p90`, percentage of weeks at ≥ 40 °C, and `level` 0/1/2 (thresholds of ≥ 35 °C and ≥ 40 °C). |
| `lst.hot_months`, `lst.hottest` | Months with a median ≥ 35 °C and the hottest month |
| `et.yearly[]` | Annual ET and PET in mm (MOD16A3GF, 500 m) and the ET/PET ratio |
| `et.et_mm`, `et.pet_mm`, `et.ratio`, `et.stress` | Averages and observed water stress, classified as high (< 0.25), moderate (< 0.45), or low |

The service caches per-image values on disk (`cache/planetary/<collection>_<lat>_<lon>.json`), so reprocessing fetches only new composites. An empty catalog, errors in more than half of the reads, or fewer than 12 valid images result in HTTP 502. Laravel treats NDVI and terrain as optional.

## POST /v1/terrain

```json
{ "latitude": -18.9186, "longitude": -48.2772, "boundary": { "type": "Polygon", "coordinates": [[[-48.2812, -18.9156], "..."]] } }
```

Samples **SRTM GL1 (~30 m)** elevation on a 5 × 5 grid across the field boundary, or a 300 m square around the point, via the public OpenTopoData API.

| Field | Contents |
|---|---|
| `slope_pct` | Mean, P90, and maximum slope (%) |
| `elevation_m` | Minimum, maximum, and mean elevation |
| `relief_class` | Embrapa terrain class. The API values are `plano` (flat), `suave ondulado` (gently rolling), `ondulado` (rolling), `forte ondulado` (steep rolling), `montanhoso` (mountainous), and `escarpado` (escarpment). |
| `ls_factor`, `ls_relative` | RUSLE topographic factor and its ratio relative to a 3% slope (1.0 is neutral) |
| `slope_length_assumed_m` | Assumed slope length (100 m) |
| `dataset`, `resolution_m`, `source_note`, `citation`, `fetched_at`, `grid` | Traceability information |

Failures return HTTP 502 with a `problem+json` response. Terrain is optional in Laravel. It stores `null` and continues the analysis, while the engine records the information gap.

## POST /v1/climate-profile

```json
{ "latitude": -18.9186, "longitude": -48.2772, "start_year": 2005, "end_year": 2025 }
```

Returns a **ClimateProfile**. See the [full synthetic example](exemplos/climate-profile.sintetico.json), which uses test data.

| Field | Contents |
|---|---|
| `source` | Dataset, API version, parameters with units and long names, period, location, `fetched_at`, messages, missing optional parameters, resolution note, and citation |
| `monthly[12]` | Rainfall (mean, P10/P50/P90, and by year), ETo (mean and by year), water balance, Tmax/Tmin/Tmean, heat days by threshold (28–42 °C), frost probability by threshold (−2 to 6 °C), longest dry spell, extreme rainfall days, and soil moisture |
| `season` | Longest dry spell by growing season (October–March) and percentages of seasons with spells of ≥ 10 and ≥ 15 days |
| `extremes` | P95 of wet days and 1-day and 5-day maxima |
| `yearly`, `trends`, `recent` | Annual series, Sen’s slope and the Mann–Kendall test, and anomalies over the past 3 years |
| `calendar[12]` | Risk levels 0/1/2 for heat, frost, drought, and heavy rainfall |
| `confidence` | Value (0–0.6 for gridded data) and notes |

Laravel stores this JSON in `field_analyses.climate`, terrain in `field_analyses.terrain`, NDVI in `field_analyses.vegetation`, and stress in `field_analyses.stress`. It sends these values back to `/v1/analysis`.

## POST /v1/analysis

See the [example request](exemplos/analysis-request.json). The request body has this shape:

```json
{
  "climate": { "...": "ClimateProfile" },
  "terrain": { "...": "Response from /v1/terrain or null" },
  "vegetation": { "...": "Response from /v1/vegetation or null" },
  "stress": { "...": "Response from /v1/stress or null" },
  "earthdata": { "...": "Response from /v1/earthdata or null" },
  "field": { "latitude": -18.9186, "longitude": -48.2772, "area_ha": 48.5, "irrigated": false, "irrigation_mm_day": null },
  "soil": { "source": "lab_analysis|farmer_estimate|unknown", "texture": "arenosa|media|argilosa|muito_argilosa", "ph_water": 5.6, "v_pct": 55 },
  "history": [{ "crop": "soja", "sown_at": "2024-10-25", "harvested_at": "2025-02-20" }],
  "priorities": { "save_water": 4, "soil_structure": 3, "n_fixation": 2, "erosion_control": 4, "organic_matter": 3,
                  "pest_break": 3, "forage": 2, "extra_income": 4, "market_fit": 3 },
  "constraints": { "excluded_crops": [], "buyer_crops": ["soja"], "no_buyer_crops": [], "missing_equipment": [], "has_livestock": true },
  "scenario": { "rain_delta_pct": 0, "temp_delta_c": 0 }
}
```

See the response types in `resources/js/types/contract.ts` and the [synthetic response example](exemplos/analysis.sintetico.json).

| Field | Contents |
|---|---|
| `disclaimer` | Reminder that growers and local advisors make the final decisions |
| `weights[]` | Weight used for each criterion (`climate_risk` has a fixed weight of 3) |
| `diagnosis` | Calendar showing bare soil and the current crop, vulnerable months for the current crop, findings with sources and periods, chart series, source, confidence, and the applied scenario |
| `strategies[]` | Strategy A (the current rotation, when crop history is available) and up to three alternatives. Includes `title`, `focus`, `steps`, `cover_by_month`, `score` (0–100), `score_range` (P10–P90 across years), `confidence` (`alta` ≥ 0.7, `media` ≥ 0.5, or `baixa`), `low_confidence_badge`, `criteria[10]` (score, weight, confidence, explanation, and difference from the current rotation), `rationale`, `evidences`, `benefits`, `information_gaps`, `local_review_risks`, and `conflicts`. |
| `discarded[]` | Rotation templates rejected by hard filters and the reasons for rejection |
| `warnings[]`, `human_judgment[]`, `sources[]` | Warnings, places where human judgment matters, and citations |

## Internal Laravel API used by Vue

Authentication uses the same-origin Laravel **session cookie** with CSRF protection. The front end sends `X-XSRF-TOKEN` with the value of the `XSRF-TOKEN` cookie.

Access is limited to the **field owner**. Anyone can view and simulate the **public demo**. HTTP 401, 403, 404, 419, and 429 errors use `problem+json` with `detail` in Portuguese.

| Method | Route | Access | Description |
|---|---|---|---|
| GET | `/api/v1/fields/{id}/status` | Owner or demo visitor | Returns `{status, message, analyzed_at}` |
| POST | `/api/v1/fields/{id}/process[?force=1]` | Owner or demo visitor | Runs processing synchronously with a lock |
| GET | `/api/v1/fields/{id}/analysis?rain_delta_pct=&temp_delta_c=&priorities[k]=` | Owner or demo visitor | Forwards the request to `/v1/analysis` (30-minute cache per payload). Optional `priorities` simulate weights without saving them. |
| PUT | `/api/v1/farms/{id}/priorities` | Signed-in owner | Saves priority weights from 0 to 5 |
| POST | `/api/v1/fields/{id}/feedback` | Owner or demo visitor | Records “Makes sense,” “Needs adjustment,” or “Not applicable” |
