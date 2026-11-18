# Rotation engine (B5) — rules

The deterministic engine in `geo-service/app/engine/` lets users trace every score to the data and rules behind it.

## 1. Current rotation

The engine uses the 12 months ending at the most recent harvest in the reported history. It flags months with ≥ 15 days without a crop as **bare soil**.

## 2. Candidate rotations

The engine uses 10 Cerrado templates in `catalog/templates.json`. These include intercropping (corn and brachiaria) and cover stages during the dry season. The engine skips the water check for those cover stages because the plants are already established.

## 3. Hard filters and reasons for rejection

1. The grower excluded the crop.
2. Required equipment is unavailable, such as a small-seed drill.
3. Mean monthly temperature is below the crop’s base temperature.
4. Frost occurs in ≥ 30% of years for crops with no frost tolerance or ≥ 50% of years for crops with low tolerance.
5. **Water.** The monthly balance, including stored soil water, shows a shortfall of more than 50% of ETc in ≥ 50% of years. This threshold is less restrictive than the “×1.2” rule in document 06, which excluded second-season corn, a common regional crop.
6. Soil pH is below the crop minimum minus 1.0 or above the maximum plus 0.5, with no feasible amendment.
7. Consecutive crops belong to the same botanical family and both host a pest or disease favored by that sequence, such as white mold, cyst nematode, or corn leafhopper. For example, **soybeans → beans**.

## 4. Criteria (0–100)

| Criterion (weighted by the grower’s star rating) | Calculation |
|---|---|
| Water use | Monthly balance **year by year**. ETc = ETo × Kc (initial, midseason, or final stage) × fraction of the month. Supply = 0.8 × rainfall + irrigation + stored soil water (40/70/100/110 mm by texture). Score = 100 × (1 − 1.6 × median deficit), with a bonus for drought-tolerant crops in areas with dry spells. The P10–P90 range across years gives the score range. |
| Soil structure | Deep roots +25, medium roots +12, shallow roots +5. Mixing taproots and fibrous roots adds 10. Each month without live plants subtracts 5. |
| Nitrogen | Catalog nitrogen credit. 120 kg/ha scores 100. |
| Erosion | Protection against erosive rainfall. P = Σ (monthly rainfall² × cover) / Σ rainfall². Cover factors are 1.0 for an active crop, 0.8 for dormant cover, 0.4–0.7 for residue (by C:N ratio), and 0.5 in the planting month. **Terrain (SRTM).** Score = 100 × [1 − (1 − P) × LS/LS₃%]. The engine uses the RUSLE LS factor (S from McCool 1987, L from Wischmeier & Smith 1978, and a 100 m slope length) and limits it to 0.4–2.5 times the factor for a 3% slope. When terrain data are missing, LS/LS₃% = 1 and the confidence multiplier drops from 0.95 to 0.85. |
| Organic matter | Residue (t/ha) × C:N factor (1.2 / 1.0 / 0.7). A value of 16 scores 100. |
| Pests | Key pests are those hosted by the current cash crops. Use the strongest break in the rotation (suppressive crop 1.0, nonhost 0.7, poor host 0.5) × 75, add a crop family diversity bonus (+15/+25), and subtract 10 if the same crop repeats. |
| Forage | Forage value from May through September. |
| Additional income | Market index for cash crops beyond the main crop (assumption). |
| Market | Known buyer 100, unknown buyer 50, no buyer 0. |
| **Climate resilience** (fixed weight of 3) | 1 − P(loss), combining frost, heat above the crop threshold during the sensitive stage, and dry spells, weighted by crop tolerance. |

Final score = Σ (weight × score) / Σ weights. Overall confidence is the weighted average of confidence across criteria. Below 0.5, the tool displays a **“Low confidence — check with an advisor”** badge.

## 5. Selection

Show strategy A (current rotation) and the three highest-scoring alternatives **with crop diversity**. Reject a candidate if its crop Jaccard similarity to an already selected option exceeds 0.6, or exceeds 0.3 and the two options share the same dominant criterion.

## 6. Explanations

Templates turn the numbers into a rationale (field context, strategy focus, and largest gain over the current rotation), evidence (text, dataset, and period), benefits (gains ≥ 10 points, fewer months with bare soil, lower water deficit, and nitrogen), information gaps (soil, market, slope, data resolution, and catalog assumptions), risks to review locally (catalog risks and climate risks ≥ 25%), and trade-offs (a criterion ≥ 70 alongside another ≤ 35).

The diagnosis includes a terrain finding sourced from SRTM. It flags a risk to review locally when mean slope is ≥ 12% and there is bare soil in rainy months, and shows a general warning when mean slope is ≥ 20% (steep rolling terrain).

## 7. Scenarios

Multiply rainfall by (1 + Δ%) and add ΔT to temperatures. Recalculate heat days and frost using shifted thresholds. Multiply ETo by (1 + 0.03 × ΔT). The interface explains that dry spells and extreme rainfall retain their historical values.
