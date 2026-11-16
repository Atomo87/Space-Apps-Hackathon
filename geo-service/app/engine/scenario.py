"""Cenários "E se…?" — RF07. Ajusta o perfil climático histórico sem refazer a consulta à NASA.

- Chuva: todos os totais mensais × (1 + Δ%).
- Temperatura: +ΔT nas médias; dias de calor e probabilidade de geada são relidos com o
  limiar deslocado (dias com Tmax + ΔT ≥ L  ⇔  Tmax ≥ L − ΔT), usando as contagens já calculadas.
- ETo: +3% por °C (aproximação da sensibilidade do Penman-Monteith; documentada como tal).
- Veranicos e chuva extrema não são alterados (limitação declarada).
"""

from __future__ import annotations

import copy
from typing import Any

from app.i18n import tr as translate
from app.climate.indicators import build_calendar

ETO_PER_DEGREE = 0.03


def _interp(table: dict[str, float | None], x: float) -> float | None:
    pts = sorted((float(k), v) for k, v in table.items() if v is not None)
    if not pts:
        return None
    if x <= pts[0][0]:
        return pts[0][1]
    if x >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 != x0 else y0
    return None


def apply_scenario(profile: dict[str, Any], rain_delta_pct: float, temp_delta_c: float) -> dict[str, Any]:
    if not rain_delta_pct and not temp_delta_c:
        return profile
    p = copy.deepcopy(profile)
    f = 1 + rain_delta_pct / 100
    g = 1 + ETO_PER_DEGREE * temp_delta_c
    for mo in p["monthly"]:
        mo["rain_mm"] = {k: (None if v is None else round(v * f, 1)) for k, v in mo["rain_mm"].items()}
        mo["rain_by_year"] = {k: (None if v is None else round(v * f, 1)) for k, v in mo["rain_by_year"].items()}
        if mo["eto_mm"] is not None:
            mo["eto_mm"] = round(mo["eto_mm"] * g, 1)
        mo["eto_by_year"] = {k: (None if v is None else round(v * g, 1)) for k, v in mo["eto_by_year"].items()}
        if mo["rain_mm"]["mean"] is not None and mo["eto_mm"] is not None:
            mo["water_balance_mm"] = round(mo["rain_mm"]["mean"] - mo["eto_mm"], 1)
        for k in ("tmax_c", "tmin_c", "tmean_c"):
            if mo[k] is not None:
                mo[k] = round(mo[k] + temp_delta_c, 1)
        old_heat, old_frost = mo["heat_days"], mo["frost_prob"]
        mo["heat_days"] = {k: _round(_interp(old_heat, float(k) - temp_delta_c), 2) for k in old_heat}
        mo["frost_prob"] = {k: _round(_interp(old_frost, float(k) - temp_delta_c), 3) for k in old_frost}
    p["calendar"] = build_calendar(p["monthly"])
    p["scenario_applied"] = {
        "rain_delta_pct": rain_delta_pct,
        "temp_delta_c": temp_delta_c,
        "notes": [
            translate("Cenário aplicado sobre a climatologia histórica (não é previsão)."),
            translate("ETo ajustada em +3% por °C (aproximação)."),
            translate("Veranicos e chuvas extremas mantidos como no histórico."),
        ],
    }
    return p


def _round(x: float | None, nd: int) -> float | None:
    return None if x is None else round(x, nd)
