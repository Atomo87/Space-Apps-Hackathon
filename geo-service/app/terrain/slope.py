"""Relevo do talhão a partir de uma grade de elevação (SRTM) — declividade e fator LS da RUSLE.

Funções puras (sem rede), testáveis com grades sintéticas.

Referências:
- Declividade por diferenças centrais numa grade regular (Horn simplificado).
- Fator S: McCool et al. (1987), usado na RUSLE (Renard et al., 1997, USDA Agriculture Handbook 703).
- Fator L: Wischmeier & Smith (1978), expoente m pela declividade.
- Classes de relevo: Embrapa, Sistema Brasileiro de Classificação de Solos (plano 0–3 %, suave ondulado 3–8 %,
  ondulado 8–20 %, forte ondulado 20–45 %, montanhoso 45–75 %, escarpado > 75 %).
"""

from __future__ import annotations

import math
from typing import Any

EARTH_M_PER_DEG_LAT = 111_320.0
SLOPE_LENGTH_ASSUMED_M = 100.0  # comprimento de rampa típico de lavoura sem terraço (hipótese a validar)
REFERENCE_SLOPE_PCT = 3.0  # relevo "suave" de referência: nessa declividade o LS não muda a nota de erosão
GRID_N = 5  # 5 × 5 = 25 pontos por talhão (uma chamada à API)
MIN_SIDE_M = 150.0  # menor lado da grade (≥ 5 pixels SRTM de 30 m)
MAX_SIDE_M = 3_000.0

RELIEF_CLASSES = [
    (3.0, "plano"),
    (8.0, "suave ondulado"),
    (20.0, "ondulado"),
    (45.0, "forte ondulado"),
    (75.0, "montanhoso"),
    (math.inf, "escarpado"),
]


def relief_class(slope_pct: float) -> str:
    return next(name for limit, name in RELIEF_CLASSES if slope_pct < limit)


def m_per_deg_lon(lat: float) -> float:
    return EARTH_M_PER_DEG_LAT * math.cos(math.radians(lat))


def sample_grid(lat: float, lon: float, boundary: dict[str, Any] | None = None, n: int = GRID_N) -> dict[str, Any]:
    """Grade n × n cobrindo o polígono do talhão (ou um quadrado de 300 m no centróide)."""
    if boundary and boundary.get("type") == "Polygon" and boundary.get("coordinates"):
        ring = boundary["coordinates"][0]
        lons = [float(p[0]) for p in ring]
        lats = [float(p[1]) for p in ring]
        lat0, lat1, lon0, lon1 = min(lats), max(lats), min(lons), max(lons)
        clat, clon = (lat0 + lat1) / 2, (lon0 + lon1) / 2
        h_m = (lat1 - lat0) * EARTH_M_PER_DEG_LAT
        w_m = (lon1 - lon0) * m_per_deg_lon(clat)
    else:
        clat, clon, h_m, w_m = lat, lon, 300.0, 300.0
    h_m = min(MAX_SIDE_M, max(MIN_SIDE_M, h_m))
    w_m = min(MAX_SIDE_M, max(MIN_SIDE_M, w_m))
    dlat = h_m / EARTH_M_PER_DEG_LAT
    dlon = w_m / m_per_deg_lon(clat)
    rows = []
    for i in range(n):  # norte → sul
        la = clat + dlat / 2 - dlat * i / (n - 1)
        rows.append([(round(la, 6), round(clon - dlon / 2 + dlon * j / (n - 1), 6)) for j in range(n)])
    return {"points": rows, "dx_m": w_m / (n - 1), "dy_m": h_m / (n - 1)}


def slope_grid(z: list[list[float | None]], dx: float, dy: float) -> list[float]:
    """Declividade (%) em cada célula interna com os 4 vizinhos válidos."""
    out = []
    for i in range(1, len(z) - 1):
        for j in range(1, len(z[0]) - 1):
            e, w, n, s = z[i][j + 1], z[i][j - 1], z[i - 1][j], z[i + 1][j]
            if None in (e, w, n, s):
                continue
            gx = (e - w) / (2 * dx)
            gy = (n - s) / (2 * dy)
            out.append(100.0 * math.hypot(gx, gy))
    return out


def s_factor(slope_pct: float) -> float:
    theta = math.atan(slope_pct / 100.0)
    return 10.8 * math.sin(theta) + 0.03 if slope_pct < 9 else 16.8 * math.sin(theta) - 0.50


def l_factor(slope_pct: float, length_m: float = SLOPE_LENGTH_ASSUMED_M) -> float:
    m = 0.2 if slope_pct < 1 else 0.3 if slope_pct < 3 else 0.4 if slope_pct < 4.5 else 0.5
    return (length_m / 22.13) ** m


def ls_factor(slope_pct: float, length_m: float = SLOPE_LENGTH_ASSUMED_M) -> float:
    return l_factor(slope_pct, length_m) * s_factor(slope_pct)


LS_REFERENCE = ls_factor(REFERENCE_SLOPE_PCT)


def _pct(vals: list[float], q: float) -> float:
    v = sorted(vals)
    pos = (len(v) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def summarize(z: list[list[float | None]], dx: float, dy: float) -> dict[str, Any]:
    flat = [v for row in z for v in row if v is not None]
    slopes = slope_grid(z, dx, dy)
    if len(flat) < 9 or not slopes:
        raise ValueError("Elevação insuficiente para calcular a declividade.")
    mean_slope = sum(slopes) / len(slopes)
    p90 = _pct(slopes, 0.9)
    ls = ls_factor(mean_slope)
    return {
        "slope_pct": {"mean": round(mean_slope, 1), "p90": round(p90, 1), "max": round(max(slopes), 1)},
        "elevation_m": {"min": round(min(flat)), "max": round(max(flat)), "mean": round(sum(flat) / len(flat))},
        "relief_class": relief_class(mean_slope),
        "ls_factor": round(ls, 2),
        "ls_relative": round(ls / LS_REFERENCE, 2),
        "slope_length_assumed_m": SLOPE_LENGTH_ASSUMED_M,
        "grid": {"n": len(z), "dx_m": round(dx), "dy_m": round(dy), "valid_points": len(flat), "slope_cells": len(slopes)},
    }
