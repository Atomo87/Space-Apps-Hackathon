# Historical indicators (B3) — documented rules

The source is the NASA POWER daily point API for the `ag` community, using local solar time (LST) and metric units. The default period is **2005–2025** (21 full years), retrieved through cached annual requests.

Required variables are `T2M`, `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `PRECTOTCORR`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN`, and `PS`. The optional variables are `GWETROOT` and `GWETTOP`. If the API returns HTTP 422, the client retries without the optional variables and records the gap.

## Data handling

- Convert the `fill_value` (−999) to `null` and align series by date.
- Exclude months with fewer than **90%** valid days from averages. At coverage between 90% and 100%, scale totals in proportion to the number of valid days.
- A day with missing data breaks the dry-day count.
- Read the radiation unit from `parameters.ALLSKY_SFC_SW_DWN.units` and convert it explicitly. Skip the ETo calculation if the unit is unknown.

## Indicators

| Indicator | Rule |
|---|---|
| Monthly rainfall | Sum of valid days. Report the mean, P10, P50, and P90 across years. |
| **ETo** | Daily FAO-56 Penman–Monteith. Calculate `ea` from dew point (equation 14), with mean relative humidity as the fallback (equation 19). Use `G = 0`, an albedo of 0.23, and elevation to calculate Rso. Automated tests check FAO-56 examples 8 and 18. |
| Water balance | Mean rainfall − mean ETo (mm/month). |
| Heat days | Days with Tmax ≥ L for L = 28–42 °C, averaged by month. The calendar uses 34 °C. The engine uses the threshold for each crop. |
| Frost risk | Fraction of years with at least one day in the month with Tmin ≤ L for L = −2 to 6 °C. The reference is **2 °C** in a weather shelter because leaves can freeze before the air reaches 0 °C. |
| Dry spell | Longest run of days with rainfall below **1 mm**, by month and by growing season (October–March). Includes the percentage of seasons with runs of ≥ 10 and ≥ 15 days. |
| Extreme rainfall | Days above the **P95** of wet days (≥ 1 mm), plus annual 1-day and 5-day maxima. |
| Trend | Sen’s slope (per decade) and the two-sided Mann–Kendall test for annual rainfall, Tmax, and Tmin. The diagnosis reports trends only when p < 0.1. |
| Recent anomaly | The last 3 years compared with the full-period mean. |
| Soil moisture | Monthly mean of `GWETROOT` (0–1, MERRA-2 model). |

## Vulnerability calendar (0 = low, 1 = caution, 2 = high)

| Risk | 1 | 2 |
|---|---|---|
| Heat | ≥ 2 days/month with Tmax ≥ 34 °C | ≥ 5 days |
| Frost | P(Tmin ≤ 2 °C) ≥ 10% | ≥ 30% |
| Drought | Water balance < −20 mm, or an average dry spell ≥ 7 days (October–March) | Water balance < −60 mm, or a dry spell ≥ 10 days |
| Heavy rainfall | ≥ 0.5 day/month above P95 | ≥ 1 day |
| Bare soil | ≥ 15 days without a crop during the month, based on the reported history, outside the rainy season | Same threshold during the rainy season |

## Confidence

For regional grid data without local calibration, the confidence limit is **0.6** × the coverage of key variables. Catalog-based criteria range from 0.4 to 0.55. A known buyer raises market confidence to 0.8. A soil test increases confidence in the water-use criterion.
