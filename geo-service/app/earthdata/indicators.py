"""Indicadores dos conjuntos NASA Earthdata (funções puras, sem rede).

- SMAP (umidade do solo superficial, 9 km): mês a mês e situação recente.
- GPM IMERG (chuva mensal por satélite, 0,1°): climatologia e comparação com a NASA POWER.
- ECOSTRESS (índice de estresse evaporativo, 70 m): passagens sem nuvem sobre o talhão.
- GRACE/GRACE-FO (água total armazenada, mascons ~300 km): tendência e anomalia recente.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import fmean, median
from typing import Any

from app.climate.indicators import MONTH_NAMES, mann_kendall_p, percentile, r, sen_slope


# ------------------------------------------------------------------ SMAP
def summarize_smap(obs: list[dict[str, Any]], today: date | None = None) -> dict[str, Any]:
    """``obs``: ``{"date", "sm"}`` (m³/m³, já filtrado) → climatologia mensal e nível relativo de secura."""
    today = today or date.today()
    pts = sorted((date.fromisoformat(o["date"]), float(o["sm"])) for o in obs if o.get("sm") is not None and 0 <= o["sm"] <= 0.7)
    if len(pts) < 20:
        raise ValueError("Poucas passagens do SMAP com umidade válida neste ponto.")
    by_m: dict[int, list[float]] = defaultdict(list)
    for d, v in pts:
        by_m[d.month].append(v)
    p50s = {m: percentile(v, 0.5) for m, v in by_m.items() if len(v) >= 2}
    lo, hi = (min(p50s.values()), max(p50s.values())) if p50s else (0, 0)
    span = (hi - lo) or 1e-9
    monthly = []
    for m in range(1, 13):
        p50 = p50s.get(m)
        frac = None if p50 is None else (p50 - lo) / span
        monthly.append({"month": m, "name": MONTH_NAMES[m - 1], "n": len(by_m.get(m, [])), "p50": r(p50, 3),
                        "p10": r(percentile(by_m[m], 0.1), 3) if p50 is not None else None,
                        # Secura relativa ao próprio ponto: o solo arenoso nunca fica tão úmido quanto o argiloso.
                        "level": 0 if frac is None else 2 if frac < 0.25 else 1 if frac < 0.5 else 0})
    recent = [v for d, v in pts if (today - d).days <= 30]
    rec_months = {d.month for d, v in pts if (today - d).days <= 30}
    clim = [p50s[m] for m in rec_months if m in p50s]
    rec = fmean(recent) if recent else None
    known = [m for m in monthly if m["p50"] is not None]
    return {
        "monthly": monthly,
        "dry_months": [m["month"] for m in monthly if m["level"] == 2],
        "wettest": max(known, key=lambda m: m["p50"])["name"] if known else None,
        "driest": min(known, key=lambda m: m["p50"])["name"] if known else None,
        "recent": {"sm": r(rec, 3), "n": len(recent), "anomaly": r(rec - fmean(clim), 3) if rec is not None and clim else None},
        "series": [{"date": d.isoformat(), "sm": round(v, 3)} for d, v in pts],
        "coverage": {"observations": len(obs), "valid": len(pts), "start": pts[0][0].isoformat(), "end": pts[-1][0].isoformat()},
    }


# ------------------------------------------------------------------ GPM IMERG
def summarize_gpm(obs: list[dict[str, Any]], power_monthly_mm: dict[int, float] | None = None) -> dict[str, Any]:
    """``obs``: ``{"month": "AAAA-MM", "mm"}`` (chuva do mês) → médias mensais, ano a ano e comparação com o POWER."""
    pts = sorted((o["month"], float(o["mm"])) for o in obs if o.get("mm") is not None and o["mm"] >= 0)
    if len(pts) < 24:
        raise ValueError("Menos de 2 anos de chuva GPM IMERG para este ponto.")
    by_m: dict[int, list[float]] = defaultdict(list)
    by_y: dict[int, list[float]] = defaultdict(list)
    for ym, mm in pts:
        by_m[int(ym[5:7])].append(mm)
        by_y[int(ym[:4])].append(mm)
    monthly = [{"month": m, "name": MONTH_NAMES[m - 1], "mean_mm": r(fmean(by_m[m]), 0) if by_m.get(m) else None,
                "p10_mm": r(percentile(by_m[m], 0.1), 0) if by_m.get(m) else None} for m in range(1, 13)]
    annual = sum(m["mean_mm"] or 0 for m in monthly)
    yearly = [{"year": y, "mm": round(sum(v))} for y, v in sorted(by_y.items()) if len(v) == 12]
    last12 = sum(mm for _, mm in pts[-12:])
    out: dict[str, Any] = {
        "monthly": monthly,
        "annual_mm": round(annual),
        "yearly": yearly,
        "last12_mm": round(last12),
        "last12_anomaly_pct": round(100 * (last12 / annual - 1)) if annual else None,
        "coverage": {"months": len(pts), "start": pts[0][0], "end": pts[-1][0]},
    }
    if power_monthly_mm:
        power_annual = sum(power_monthly_mm.values())
        out["power_annual_mm"] = round(power_annual)
        out["vs_power_pct"] = round(100 * (annual / power_annual - 1)) if power_annual else None
    return out


# ------------------------------------------------------------------ ECOSTRESS
ESI_HIGH_STRESS = 0.3
ESI_MODERATE = 0.6


def summarize_ecostress(obs: list[dict[str, Any]]) -> dict[str, Any]:
    """``obs``: ``{"datetime", "esi"}`` (0–1; 1 = sem estresse) de passagens sem nuvem."""
    pts = sorted((o["datetime"], float(o["esi"])) for o in obs if o.get("esi") is not None and 0 <= o["esi"] <= 1.5)
    if len(pts) < 3:
        raise ValueError("Menos de 3 passagens do ECOSTRESS sem nuvem sobre o talhão.")
    vals = [min(v, 1.0) for _, v in pts]
    by_m: dict[int, list[float]] = defaultdict(list)
    for t, v in pts:
        by_m[int(t[5:7])].append(min(v, 1.0))
    med = median(vals)
    return {
        "observations": [{"datetime": t, "esi": round(min(v, 1.0), 3)} for t, v in pts],
        "median_esi": round(med, 3),
        "high_stress_pct": round(100 * sum(v < ESI_HIGH_STRESS for v in vals) / len(vals)),
        "by_month": [{"month": m, "name": MONTH_NAMES[m - 1], "median": round(median(v), 3), "n": len(v)} for m, v in sorted(by_m.items())],
        "latest": {"datetime": pts[-1][0], "esi": round(min(pts[-1][1], 1.0), 3)},
        "stress": "alto" if med < ESI_HIGH_STRESS else "moderado" if med < ESI_MODERATE else "baixo",
        "thresholds": {"high_below": ESI_HIGH_STRESS, "moderate_below": ESI_MODERATE},
    }


# ------------------------------------------------------------------ GRACE
def summarize_grace(obs: list[dict[str, Any]]) -> dict[str, Any]:
    """``obs``: ``{"date", "cm"}`` (anomalia de água equivalente, cm, em relação a 2004–2009)."""
    pts = sorted((date.fromisoformat(o["date"]), float(o["cm"])) for o in obs if o.get("cm") is not None)
    if len(pts) < 24:
        raise ValueError("Série GRACE curta demais para este ponto.")
    by_y: dict[int, list[float]] = defaultdict(list)
    for d, v in pts:
        by_y[d.year].append(v)
    yearly = [(y, fmean(v)) for y, v in sorted(by_y.items()) if len(v) >= 6]
    xs, ys = [float(y) for y, _ in yearly], [v for _, v in yearly]
    slope = sen_slope(xs, ys)
    recent = pts[-12:]
    worst = min(pts, key=lambda p: p[1])
    return {
        "series": [{"date": d.isoformat(), "cm": round(v, 2)} for d, v in pts],
        "yearly": [{"year": y, "cm": round(v, 2)} for y, v in yearly],
        "trend_cm_per_decade": r(slope * 10 if slope is not None else None, 1),
        "trend_p_value": r(mann_kendall_p(ys), 3),
        "latest": {"date": pts[-1][0].isoformat(), "cm": round(pts[-1][1], 1)},
        "recent12_mean_cm": round(fmean(v for _, v in recent), 1),
        "record_low": {"date": worst[0].isoformat(), "cm": round(worst[1], 1)},
        "coverage": {"months": len(pts), "start": pts[0][0].isoformat(), "end": pts[-1][0].isoformat()},
    }
