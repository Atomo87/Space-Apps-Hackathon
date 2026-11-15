"""Evapotranspiração de referência diária — FAO-56 Penman-Monteith (Allen et al., 1998).

Equações citadas pelo número do boletim FAO-56. Entradas no SI:
temperaturas em °C, vento a 2 m em m/s, radiação solar em MJ m⁻² dia⁻¹, pressão em kPa.
"""

from __future__ import annotations

import math
from datetime import date

GSC = 0.0820  # constante solar, MJ m-2 min-1
SIGMA = 4.903e-9  # Stefan-Boltzmann, MJ K-4 m-2 dia-1


def sat_vapour_pressure(t: float) -> float:
    """e°(T), kPa (eq. 11)."""
    return 0.6108 * math.exp(17.27 * t / (t + 237.3))


def extraterrestrial_radiation(lat_deg: float, day: date) -> float:
    """Ra, MJ m-2 dia-1 (eqs. 21–25)."""
    j = day.timetuple().tm_yday
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi / 365 * j)
    delta = 0.409 * math.sin(2 * math.pi / 365 * j - 1.39)
    x = -math.tan(phi) * math.tan(delta)
    ws = math.acos(max(-1.0, min(1.0, x)))
    return (24 * 60 / math.pi) * GSC * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws)
    )


def pressure_from_elevation(z_m: float) -> float:
    """P, kPa (eq. 7)."""
    return 101.3 * ((293 - 0.0065 * z_m) / 293) ** 5.26


def eto_penman_monteith(
    *,
    tmax: float,
    tmin: float,
    rs: float,
    u2: float,
    lat_deg: float,
    day: date,
    elevation_m: float = 0.0,
    pressure_kpa: float | None = None,
    tdew: float | None = None,
    rh_mean: float | None = None,
) -> float | None:
    """ETo em mm/dia (eq. 6). Retorna ``None`` se faltar umidade."""
    tmean = (tmax + tmin) / 2
    p = pressure_kpa if pressure_kpa is not None else pressure_from_elevation(elevation_m)
    gamma = 0.665e-3 * p  # eq. 8
    delta = 4098 * sat_vapour_pressure(tmean) / (tmean + 237.3) ** 2  # eq. 13
    es = (sat_vapour_pressure(tmax) + sat_vapour_pressure(tmin)) / 2  # eq. 12
    if tdew is not None:
        ea = sat_vapour_pressure(tdew)  # eq. 14 (preferida)
    elif rh_mean is not None:
        ea = rh_mean / 100 * es  # eq. 19
    else:
        return None
    ea = min(ea, es)

    ra = extraterrestrial_radiation(lat_deg, day)
    rso = (0.75 + 2e-5 * elevation_m) * ra  # eq. 37
    rns = (1 - 0.23) * rs  # eq. 38 (albedo 0,23)
    ratio = min(1.0, rs / rso) if rso > 0 else 0.5
    rnl = (
        SIGMA
        * (((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2)
        * (0.34 - 0.14 * math.sqrt(max(ea, 0.0)))
        * (1.35 * ratio - 0.35)
    )  # eq. 39
    rn = rns - rnl
    g = 0.0  # fluxo de calor no solo ≈ 0 em escala diária (eq. 42)

    num = 0.408 * delta * (rn - g) + gamma * (900 / (tmean + 273)) * u2 * (es - ea)
    den = delta + gamma * (1 + 0.34 * u2)
    return max(0.0, num / den)


def radiation_to_mj(value: float, units: str) -> float | None:
    """Converte a radiação para MJ m-2 dia-1 conforme a unidade informada pela API (doc 10, §4)."""
    u = units.replace(" ", "").lower()
    if u in {"mj/m^2/day", "mj/m2/day", "mjm-2day-1"}:
        return value
    if u in {"kw-hr/m^2/day", "kwh/m^2/day", "kwh/m2/day"}:
        return value * 3.6
    if u in {"w/m^2", "w/m2"}:  # média diária em W/m²
        return value * 0.0864
    return None
