"""Estresse térmico e hídrico observados por satélite (funções puras, sem rede).

- Temperatura da superfície (MODIS LST, 8 dias, 1 km): quão quente fica o chão/dossel durante o dia.
  Lavoura verde e com água transpira e fica perto da temperatura do ar; solo exposto ou planta
  sem água esquenta bem acima dela.
- Evapotranspiração real × potencial (MODIS ET/PET anual, 500 m): a razão ET/PET é um índice de
  estresse evaporativo — quanto menor, mais a vegetação deixou de evaporar por falta de água.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.climate.indicators import MONTH_NAMES, percentile, r

LST_SCALE = 0.02  # K
HOT_SURFACE_C = 40.0  # superfície acima disso: solo exposto ou dossel sob forte estresse
WARM_SURFACE_C = 35.0
ET_SCALE = 0.1  # kg/m²/ano = mm/ano
ET_FILL_MIN = 32700


def lst_c(raw: float | None, qc: float | None) -> float | None:
    """°C de um pixel LST válido. QC (bits 0–1): 0 = boa, 1 = outra qualidade aceitável."""
    if raw is None or raw <= 7500:  # 7500 × 0,02 = 150 K: limite inferior válido do produto
        return None
    if qc is not None and (int(qc) & 0b11) not in (0, 1):
        return None
    return round(raw * LST_SCALE - 273.15, 2)


def summarize_lst(obs: list[dict[str, Any]], today: date | None = None) -> dict[str, Any]:
    """``obs``: ``{"date", "lst_raw", "qc"}`` → climatologia mensal da temperatura diurna da superfície."""
    today = today or date.today()
    pts = sorted((date.fromisoformat(o["date"]), c) for o in obs if (c := lst_c(o.get("lst_raw"), o.get("qc"))) is not None)
    if len(pts) < 12:
        raise ValueError("Poucas imagens de temperatura da superfície sem nuvem.")
    by_month: dict[int, list[float]] = defaultdict(list)
    for d, c in pts:
        by_month[d.month].append(c)
    monthly = []
    for m in range(1, 13):
        vals = by_month.get(m, [])
        p50 = r(percentile(vals, 0.5), 1) if len(vals) >= 2 else None
        monthly.append({
            "month": m, "name": MONTH_NAMES[m - 1], "n": len(vals),
            "p50": p50,
            "p90": r(percentile(vals, 0.9), 1) if len(vals) >= 2 else None,
            "hot_pct": round(100 * sum(v >= HOT_SURFACE_C for v in vals) / len(vals)) if vals else None,
            "level": 0 if p50 is None else 2 if p50 >= HOT_SURFACE_C else 1 if p50 >= WARM_SURFACE_C else 0,
        })
    known = [m for m in monthly if m["p50"] is not None]
    hottest = max(known, key=lambda m: m["p50"]) if known else None
    return {
        "monthly": monthly,
        "hot_months": [m["month"] for m in known if m["p50"] >= WARM_SURFACE_C],
        "hottest": {"month": hottest["month"], "name": hottest["name"], "p50": hottest["p50"], "p90": hottest["p90"]} if hottest else None,
        "series": [{"date": d.isoformat(), "lst_c": c} for d, c in pts],
        "coverage": {"observations": len(obs), "valid": len(pts), "start": pts[0][0].isoformat(), "end": pts[-1][0].isoformat()},
        "thresholds": {"warm_c": WARM_SURFACE_C, "hot_c": HOT_SURFACE_C},
    }


def et_level(ratio: float) -> str:
    return "alto" if ratio < 0.25 else "moderado" if ratio < 0.45 else "baixo"


def summarize_et(obs: list[dict[str, Any]]) -> dict[str, Any]:
    """``obs``: ``{"year", "et_raw", "pet_raw"}`` → ET e PET anuais (mm) e a razão ET/PET."""
    years = []
    for o in sorted(obs, key=lambda x: x["year"]):
        et, pet = o.get("et_raw"), o.get("pet_raw")
        if et is None or pet is None or et >= ET_FILL_MIN or pet >= ET_FILL_MIN or pet <= 0:
            continue
        et_mm, pet_mm = et * ET_SCALE, pet * ET_SCALE
        years.append({"year": o["year"], "et_mm": round(et_mm), "pet_mm": round(pet_mm), "ratio": round(et_mm / pet_mm, 3)})
    if not years:
        raise ValueError("Sem evapotranspiração MODIS válida para este ponto (área urbana, água ou sem vegetação).")
    et_mean = sum(y["et_mm"] for y in years) / len(years)
    pet_mean = sum(y["pet_mm"] for y in years) / len(years)
    ratio = et_mean / pet_mean
    driest = min(years, key=lambda y: y["ratio"])
    return {
        "yearly": years,
        "et_mm": round(et_mean),
        "pet_mm": round(pet_mean),
        "ratio": round(ratio, 3),
        "stress": et_level(ratio),
        "driest_year": driest,
        "thresholds": {"high_below": 0.25, "moderate_below": 0.45},
    }
