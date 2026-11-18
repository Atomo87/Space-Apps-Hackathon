"""Indicadores climáticos históricos — tarefa B3.

Transforma a série diária da NASA POWER em um ``ClimateProfile`` (dicionário JSON) com
climatologia mensal, distribuições por ano, extremos, tendências e calendário de risco.
As regras e limiares estão documentados em ``docs/indicadores.md``.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date
from typing import Any

from app.climate.eto import eto_penman_monteith, radiation_to_mj
from app.config import POWER_CITATION, POWER_GRID_NOTE
from app.power.client import DailySeries

DRY_DAY_MM = 1.0
FROST_TMIN_C = 2.0
HEAT_GENERIC_C = 34.0
MIN_MONTH_COVERAGE = 0.9
RAINY_SEASON = (10, 11, 12, 1, 2, 3)
HEAT_THRESHOLDS = list(range(28, 43))  # °C, para cenários (+ΔT desloca o limiar)
FROST_THRESHOLDS = [x / 2 for x in range(-4, 13)]  # -2,0 … 6,0 °C
MONTH_NAMES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def percentile(values: list[float], q: float) -> float | None:
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return vals[lo] + (vals[hi] - vals[lo]) * (pos - lo)


def mean(values: list[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return statistics.fmean(vals) if vals else None


def r(x: float | None, nd: int = 1) -> float | None:
    return None if x is None else round(x, nd)


def sen_slope(xs: list[float], ys: list[float]) -> float | None:
    slopes = [
        (ys[j] - ys[i]) / (xs[j] - xs[i])
        for i in range(len(xs))
        for j in range(i + 1, len(xs))
        if xs[j] != xs[i]
    ]
    return statistics.median(slopes) if slopes else None


def mann_kendall_p(ys: list[float]) -> float | None:
    """p-valor bicaudal do teste de Mann-Kendall (sem correção de empates)."""
    n = len(ys)
    if n < 8:
        return None
    s = sum((ys[j] > ys[i]) - (ys[j] < ys[i]) for i in range(n) for j in range(i + 1, n))
    var = n * (n - 1) * (2 * n + 5) / 18
    z = (s - 1) / math.sqrt(var) if s > 0 else (s + 1) / math.sqrt(var) if s < 0 else 0.0
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def build_calendar(monthly: list[dict[str, Any]], rainy_season: tuple[int, ...] = RAINY_SEASON) -> list[dict[str, Any]]:
    """Calendário de risco por mês (0 = baixo, 1 = atenção, 2 = alto) — somente clima."""
    calendar = []
    for mo in monthly:
        hd = mo["heat_days"].get(str(int(HEAT_GENERIC_C))) or 0
        fp = mo["frost_prob"].get(f"{FROST_TMIN_C:.1f}") or 0
        wb = mo["water_balance_mm"]
        dry = mo["dry_spell_max_days"] or 0
        ext = mo["extreme_rain_days"] or 0
        rainy = mo["month"] in rainy_season
        drought = 0
        if wb is not None:
            drought = 2 if wb < -60 else 1 if wb < -20 else 0
        if rainy:
            drought = max(drought, 2 if dry >= 10 else 1 if dry >= 7 else 0)
        calendar.append({
            "month": mo["month"],
            "name": mo["name"],
            "heat": 2 if hd >= 5 else 1 if hd >= 2 else 0,
            "frost": 2 if fp >= 0.3 else 1 if fp >= 0.1 else 0,
            "drought": drought,
            "heavy_rain": 2 if ext >= 1 else 1 if ext >= 0.5 else 0,
        })
    return calendar


def _daily_eto(series: DailySeries) -> tuple[list[float | None], str | None]:
    units = series.units.get("ALLSKY_SFC_SW_DWN", "")
    if radiation_to_mj(1.0, units) is None:
        return [None] * len(series.dates), f"Unidade de radiação não reconhecida ('{units}'): ETo não calculada."
    tmax, tmin = series.get("T2M_MAX"), series.get("T2M_MIN")
    rs, ws = series.get("ALLSKY_SFC_SW_DWN"), series.get("WS2M")
    ps, td, rh = series.get("PS"), series.get("T2MDEW"), series.get("RH2M")
    elev = series.elevation_m or 0.0
    out: list[float | None] = []
    for i, d in enumerate(series.dates):
        if None in (tmax[i], tmin[i], rs[i], ws[i]):
            out.append(None)
            continue
        out.append(
            eto_penman_monteith(
                tmax=tmax[i], tmin=tmin[i], rs=radiation_to_mj(rs[i], units), u2=ws[i],
                lat_deg=series.latitude, day=d, elevation_m=elev,
                pressure_kpa=ps[i], tdew=td[i], rh_mean=rh[i],
            )
        )
    return out, None


def build_climate_profile(series: DailySeries, rainy_season: tuple[int, ...] = RAINY_SEASON) -> dict[str, Any]:
    dates = series.dates
    years = sorted({d.year for d in dates})
    rain = series.get("PRECTOTCORR")
    tmax, tmin, tmean = series.get("T2M_MAX"), series.get("T2M_MIN"), series.get("T2M")
    rh = series.get("RH2M")
    sm_root = series.get("GWETROOT")
    eto, eto_note = _daily_eto(series)

    # ---- agrupamento por (ano, mês)
    idx: dict[tuple[int, int], list[int]] = defaultdict(list)
    for i, d in enumerate(dates):
        idx[(d.year, d.month)].append(i)

    def month_sum(key, col) -> float | None:
        ii = idx.get(key, [])
        vals = [col[i] for i in ii if col[i] is not None]
        if not ii or len(vals) / len(ii) < MIN_MONTH_COVERAGE:
            return None
        return sum(vals) * len(ii) / len(vals)  # completa proporcionalmente as poucas falhas

    def month_mean(key, col) -> float | None:
        ii = idx.get(key, [])
        vals = [col[i] for i in ii if col[i] is not None]
        if not ii or len(vals) / len(ii) < MIN_MONTH_COVERAGE:
            return None
        return statistics.fmean(vals)

    # ---- chuva extrema: percentil 95 dos dias com chuva no período todo
    wet = [v for v in rain if v is not None and v >= DRY_DAY_MM]
    p95 = percentile(wet, 0.95) if wet else None

    # ---- maior sequência seca dentro de cada mês (falha interrompe a sequência)
    def longest_dry(ii: list[int]) -> int | None:
        if not ii:
            return None
        best = run = 0
        valid = 0
        for i in ii:
            v = rain[i]
            if v is None:
                run = 0
                continue
            valid += 1
            run = run + 1 if v < DRY_DAY_MM else 0
            best = max(best, run)
        return best if valid / len(ii) >= MIN_MONTH_COVERAGE else None

    monthly = []
    for m in range(1, 13):
        keys = [(y, m) for y in years]
        rain_by_year = {y: month_sum((y, m), rain) for y in years}
        eto_by_year = {y: month_sum((y, m), eto) for y in years}
        rain_vals = [v for v in rain_by_year.values() if v is not None]
        eto_vals = [v for v in eto_by_year.values() if v is not None]

        heat_counts = {}
        for thr in HEAT_THRESHOLDS:
            per_year = []
            for k in keys:
                ii = [i for i in idx.get(k, []) if tmax[i] is not None]
                if ii:
                    per_year.append(sum(1 for i in ii if tmax[i] >= thr))
            heat_counts[str(thr)] = r(mean(per_year), 2)

        frost_prob = {}
        frost_days = None
        for thr in FROST_THRESHOLDS:
            hits = n = 0
            days_per_year = []
            for k in keys:
                ii = [i for i in idx.get(k, []) if tmin[i] is not None]
                if not ii:
                    continue
                n += 1
                c = sum(1 for i in ii if tmin[i] <= thr)
                hits += 1 if c > 0 else 0
                days_per_year.append(c)
            frost_prob[f"{thr:.1f}"] = r(hits / n, 3) if n else None
            if thr == FROST_TMIN_C:
                frost_days = r(mean(days_per_year), 2)

        dry = [longest_dry(idx.get(k, [])) for k in keys]
        extreme = []
        for k in keys:
            ii = [i for i in idx.get(k, []) if rain[i] is not None]
            if ii and p95 is not None:
                extreme.append(sum(1 for i in ii if rain[i] > p95))

        rain_mean = mean(rain_vals)
        eto_mean = mean(eto_vals)
        sm_vals = [month_mean(k, sm_root) for k in keys]
        monthly.append({
            "month": m,
            "name": MONTH_NAMES[m - 1],
            "rain_mm": {"mean": r(rain_mean), "p10": r(percentile(rain_vals, 0.1)), "p50": r(percentile(rain_vals, 0.5)), "p90": r(percentile(rain_vals, 0.9))},
            "rain_by_year": {str(y): r(v) for y, v in rain_by_year.items()},
            "eto_mm": r(eto_mean),
            "eto_by_year": {str(y): r(v) for y, v in eto_by_year.items()},
            "water_balance_mm": r(rain_mean - eto_mean) if rain_mean is not None and eto_mean is not None else None,
            "tmax_c": r(mean([month_mean(k, tmax) for k in keys])),
            "tmin_c": r(mean([month_mean(k, tmin) for k in keys])),
            "tmean_c": r(mean([month_mean(k, tmean) for k in keys])),
            "rh_pct": r(mean([month_mean(k, rh) for k in keys])),
            "heat_days": heat_counts,
            "frost_prob": frost_prob,
            "frost_days_mean": frost_days,
            "dry_spell_max_days": r(mean(dry)),
            "extreme_rain_days": r(mean(extreme), 2),
            "soil_moisture_root": r(mean(sm_vals), 3),
            "soil_moisture_root_sd": r(statistics.pstdev([v for v in sm_vals if v is not None]), 3) if len([v for v in sm_vals if v is not None]) > 2 else None,
            "years_valid": len(rain_vals),
        })

    # ---- maior veranico por safra, inclusive em estações que atravessam dezembro
    season_spells = []
    season_wraps = rainy_season[0] > rainy_season[-1]
    for y in years[:-1] if season_wraps else years:
        ii = [i for i, d in enumerate(dates) if d.month in rainy_season
              and d.year == y + int(season_wraps and d.month < rainy_season[0])]
        if not ii:
            continue
        s = longest_dry(ii)
        if s is not None:
            season_spells.append({"season": f"{y}/{str(y + 1)[-2:]}" if season_wraps else str(y), "max_dry_spell_days": s})
    spell_vals = [s["max_dry_spell_days"] for s in season_spells]

    # ---- extremos anuais
    annual_max1, annual_max5 = [], []
    for y in years:
        ii = [i for i, d in enumerate(dates) if d.year == y]
        vals = [rain[i] for i in ii]
        if sum(v is not None for v in vals) / max(1, len(vals)) < MIN_MONTH_COVERAGE:
            continue
        clean = [v or 0.0 for v in vals]
        annual_max1.append(max(clean))
        annual_max5.append(max(sum(clean[k:k + 5]) for k in range(len(clean) - 4)))

    # ---- séries anuais e tendências
    yearly = {"years": [], "rain_mm": [], "tmax_c": [], "tmin_c": []}
    for y in years:
        rs = [monthly[m - 1]["rain_by_year"].get(str(y)) for m in range(1, 13)]
        tx = mean([tmax[i] for i, d in enumerate(dates) if d.year == y])
        tn = mean([tmin[i] for i, d in enumerate(dates) if d.year == y])
        yearly["years"].append(y)
        yearly["rain_mm"].append(r(sum(rs)) if all(v is not None for v in rs) else None)
        yearly["tmax_c"].append(r(tx, 2))
        yearly["tmin_c"].append(r(tn, 2))

    def trend(key: str) -> dict[str, Any]:
        pairs = [(y, v) for y, v in zip(yearly["years"], yearly[key]) if v is not None]
        if len(pairs) < 8:
            return {"per_decade": None, "p_value": None, "n_years": len(pairs)}
        xs, ys = [p[0] for p in pairs], [p[1] for p in pairs]
        slope = sen_slope(xs, ys)
        return {"per_decade": r(slope * 10 if slope is not None else None, 2), "p_value": r(mann_kendall_p(ys), 3), "n_years": len(pairs)}

    # ---- anomalia recente (últimos 3 anos × climatologia)
    recent_years = years[-3:]
    clim_rain = mean(yearly["rain_mm"])
    rec_rain = mean([v for y, v in zip(yearly["years"], yearly["rain_mm"]) if y in recent_years])
    clim_tx = mean(yearly["tmax_c"])
    rec_tx = mean([v for y, v in zip(yearly["years"], yearly["tmax_c"]) if y in recent_years])

    calendar = build_calendar(monthly, rainy_season)

    # ---- cobertura e confiança
    coverage = {c: r(sum(v is not None for v in series.get(c)) / max(1, len(dates)), 3) for c in series.values}
    core_cov = min((coverage.get(c) or 0) for c in ("PRECTOTCORR", "T2M_MAX", "T2M_MIN"))
    confidence = round(0.6 * core_cov, 2)  # 0,6 = teto para dado em grade regional sem calibração local
    notes = [POWER_GRID_NOTE]
    if eto_note:
        notes.append(eto_note)
    if series.missing_optional:
        notes.append("Umidade do solo (GWETROOT/GWETTOP) indisponível nesta consulta.")

    return {
        "source": {
            "dataset": "NASA POWER",
            "dataset_code": "POWER",
            "community": "ag",
            "api_version": series.api_version,
            "time_standard": "LST",
            "parameters": {c: {"units": series.units.get(c, ""), "longname": series.longnames.get(c, "")} for c in sorted(series.values)},
            "period": {"start": dates[0].isoformat(), "end": dates[-1].isoformat(), "years": len(years)},
            "location": {"latitude": series.latitude, "longitude": series.longitude, "elevation_m": series.elevation_m},
            "fetched_at": series.fetched_at,
            "messages": series.messages,
            "missing_optional": series.missing_optional,
            "grid_note": POWER_GRID_NOTE,
            "citation": POWER_CITATION,
            "requests": series.requests,
            "cache_hits": series.cache_hits,
        },
        "thresholds": {"dry_day_mm": DRY_DAY_MM, "frost_tmin_c": FROST_TMIN_C, "heat_generic_c": HEAT_GENERIC_C, "rainy_season_months": list(rainy_season), "extreme_rain_p95_mm": r(p95)},
        "coverage": coverage,
        "confidence": {"value": confidence, "notes": notes},
        "monthly": monthly,
        "season": {
            "rainy_months": list(rainy_season),
            "dry_spells": season_spells,
            "dry_spell_mean_max_days": r(mean(spell_vals)),
            "dry_spell_p90_days": r(percentile(spell_vals, 0.9)),
            "pct_seasons_dry_spell_ge_10": r(100 * sum(v >= 10 for v in spell_vals) / len(spell_vals)) if spell_vals else None,
            "pct_seasons_dry_spell_ge_15": r(100 * sum(v >= 15 for v in spell_vals) / len(spell_vals)) if spell_vals else None,
        },
        "extremes": {
            "p95_wet_day_mm": r(p95),
            "annual_max_1day_mm_mean": r(mean(annual_max1)),
            "annual_max_5day_mm_mean": r(mean(annual_max5)),
            "annual_max_1day_mm_record": r(max(annual_max1)) if annual_max1 else None,
        },
        "yearly": yearly,
        "trends": {"rain_mm": trend("rain_mm"), "tmax_c": trend("tmax_c"), "tmin_c": trend("tmin_c")},
        "recent": {
            "years": recent_years,
            "rain_anomaly_pct": r(100 * (rec_rain - clim_rain) / clim_rain) if rec_rain and clim_rain else None,
            "tmax_anomaly_c": r(rec_tx - clim_tx, 2) if rec_tx is not None and clim_tx is not None else None,
        },
        "calendar": calendar,
    }
