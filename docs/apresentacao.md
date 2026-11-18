# Demo script (J2) — 5 minutes

## 1. The problem (30 seconds)

A crop that improves soil in one place may use too much water, introduce disease, have no buyer, or fall outside the planting window elsewhere. Growers often make these decisions with limited long-term local data.

## 2. What we built (30 seconds)

**GeoSafra** uses about 21 years of daily **NASA POWER** climate data for the field location to show:

- **When** the field has bare soil.
- **Which months** pose the greatest risk to the current crop.
- **Which rotations** may help, with the reasoning, evidence, and confidence level for each.

## 3. Live demo (2 minutes 30 seconds)

1. On a phone, open the home page and show what the tool can help growers do and where it has limits.
2. **Open the Uberlândia example.** Have the analysis ready before the presentation.
3. **Diagnosis.** Show the vulnerability calendar, including heavy rain from December to March, dry conditions from May to September, and bare soil after the second-season corn harvest. Tap the question mark next to *dry spell*. Show the data source, period, and resolution.
4. **Compare.** Compare strategy A (current rotation) with B, C, and D. Open the evidence and information gaps. Show the discarded options, including soybeans followed by beans because of white mold.
5. Change a **priority**, such as setting forage to five stars. Recalculate to show the new ranking and the weight of each criterion.
6. **What if?** Set rainfall to −30% and temperature to +2 °C. Show that water and climate scores fall. Explain that the changes describe a scenario based on historical data.
7. Go back to **Edit**, enter a soil test and a known buyer, and show how confidence increases. Satellite observations show broad patterns, and field data refine the analysis.

## 4. How we use NASA data (45 seconds)

- Daily POWER data (MERRA-2/CERES) provide T2M, Tmax, Tmin, dew point, corrected precipitation, wind at 2 m, radiation, pressure, and root-zone soil moisture.
- Indicators include FAO-56 Penman–Monteith ETo (tested against FAO examples), year-by-year water balance, dry spells, frost (≤ 2 °C), heat days by crop-specific thresholds, rainfall above P95, and trends estimated with the Mann–Kendall test and Sen’s slope.
- The engine uses explainable rules and multiple criteria. Statistics provide a P10–P90 range across years, and documented rules determine the rotation ranking.

## 5. Limitations and next steps (45 seconds)

- The climate grid is about 50 km. Planned additions include **SMAP** for soil moisture, **HLS/MODIS** for NDVI and observed bare ground, **NASADEM** for slope and erosion, and **GRACE-FO** for regional water storage trends.
- Validate the assumptions marked in the crop catalog with local agronomists and cooperatives.
- The tool already stores “Makes sense” and “Needs adjustment” feedback to help refine its rules.
- **Growers and agricultural advisors make the final decisions with support from the tool.**

## Likely questions

- **Why use rules instead of AI?** The ranking must be auditable. We use statistics for diagnosis and uncertainty, and explainable rules for recommendations. Machine learning could be added once labeled yield data are available.
- **What if the field is small?** The confidence badge reflects the limits of the data, and local measurements take precedence.
- **Where do the crop numbers come from?** Kc comes from FAO-56. The catalog provides sources for the remaining values or marks them as assumptions.
