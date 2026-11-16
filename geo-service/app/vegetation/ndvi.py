"""Indicadores de cobertura verde a partir de séries NDVI MODIS (funções puras, sem rede).

Entrada: observações de composições de 16 dias ``{"date": "AAAA-MM-DD", "ndvi_raw": int | None, "reliability": int}``.
- ``ndvi_raw`` vem em escala ×10 000 (−2000…10000); −3000 = sem dado.
- ``reliability`` (pixel_reliability): 0 = bom, 1 = marginal, 2 = neve, 3 = nuvem, −1 = sem dado.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from app.climate.indicators import MONTH_NAMES, mann_kendall_p, percentile, r, sen_slope

SCALE = 0.0001
GOOD_RELIABILITY = (0, 1)
# NDVI abaixo disso, na mediana do mês: pouca vegetação verde (solo exposto, palhada seca ou pasto seco).
LOW_GREEN = 0.40
VERY_LOW_GREEN = 0.30
MIN_OBS_PER_MONTH = 2


def valid(obs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for o in obs:
        raw = o.get("ndvi_raw")
        if raw is None or raw <= -2000 or o.get("reliability") not in GOOD_RELIABILITY:
            continue
        point = {"date": o["date"], "ndvi": round(raw * SCALE, 4)}
        if o.get("image_date") and o.get("platform") in ("terra", "aqua"):
            point.update(image_date=o["image_date"], platform=o["platform"])
        out.append(point)
    return sorted(out, key=lambda point: (point["date"], point["ndvi"]))


def green_level(p50: float | None) -> int:
    """0 = cobertura verde boa, 1 = baixa, 2 = muito baixa (escala do calendário de risco)."""
    if p50 is None:
        return 0
    return 2 if p50 < VERY_LOW_GREEN else 1 if p50 < LOW_GREEN else 0


def summarize(obs: list[dict[str, Any]], today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    series = valid(obs)
    pts = [(date.fromisoformat(point["date"]), point["ndvi"]) for point in series]
    if len(pts) < 12:
        raise ValueError("Poucas observações NDVI válidas (nuvem ou falta de imagens) para resumir o talhão.")

    by_month: dict[int, list[float]] = defaultdict(list)
    for d, v in pts:
        by_month[d.month].append(v)

    monthly = []
    for m in range(1, 13):
        vals = by_month.get(m, [])
        enough = len(vals) >= MIN_OBS_PER_MONTH
        p50 = r(percentile(vals, 0.5), 3) if enough else None
        monthly.append({
            "month": m, "name": MONTH_NAMES[m - 1], "n": len(vals),
            "p10": r(percentile(vals, 0.1), 3) if enough else None,
            "p50": p50,
            "p90": r(percentile(vals, 0.9), 3) if enough else None,
            "level": green_level(p50),
        })

    known = [m for m in monthly if m["p50"] is not None]
    low_months = [m["month"] for m in known if m["p50"] < LOW_GREEN]
    peak = max(known, key=lambda m: m["p50"]) if known else None
    trough = min(known, key=lambda m: m["p50"]) if known else None

    # Situação recente: média das 3 últimas composições válidas contra a mediana histórica do mesmo mês.
    recent_pts = pts[-3:]
    rec_mean = sum(v for _, v in recent_pts) / len(recent_pts)
    clim = [next(m for m in monthly if m["month"] == d.month) for d, _ in recent_pts]
    clim_p50 = [c["p50"] for c in clim if c["p50"] is not None]
    clim_p10 = [c["p10"] for c in clim if c["p10"] is not None]
    anomaly = rec_mean - sum(clim_p50) / len(clim_p50) if clim_p50 else None
    below_p10 = bool(clim_p10) and rec_mean < sum(clim_p10) / len(clim_p10)
    last_date = recent_pts[-1][0]

    # Tendência: média anual de anos com ao menos 15 composições válidas (Sen + Mann-Kendall).
    by_year: dict[int, list[float]] = defaultdict(list)
    for d, v in pts:
        by_year[d.year].append(v)
    full = sorted((y, sum(v) / len(v)) for y, v in by_year.items() if len(v) >= 15)
    trend = {"per_year": None, "p_value": None, "years": len(full)}
    if len(full) >= 4:
        xs, ys = [float(y) for y, _ in full], [v for _, v in full]
        trend = {"per_year": r(sen_slope(xs, ys), 4), "p_value": r(mann_kendall_p(ys), 3), "years": len(full)}

    total = len(obs)
    return {
        "monthly": monthly,
        "low_green_months": low_months,
        "peak": {"month": peak["month"], "name": peak["name"], "ndvi": peak["p50"]} if peak else None,
        "trough": {"month": trough["month"], "name": trough["name"], "ndvi": trough["p50"]} if trough else None,
        "recent": {
            "date": last_date.isoformat(),
            "days_ago": (today - last_date).days,
            "ndvi": r(rec_mean, 3),
            "anomaly": r(anomaly, 3),
            "below_p10": below_p10,
        },
        "trend": trend,
        "series": series,
        "coverage": {
            "observations": total,
            "valid": len(pts),
            "valid_pct": round(100 * len(pts) / total) if total else 0,
            "start": pts[0][0].isoformat(),
            "end": last_date.isoformat(),
        },
        "thresholds": {"low_green": LOW_GREEN, "very_low_green": VERY_LOW_GREEN},
    }
