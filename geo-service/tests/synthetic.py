"""Gerador de série diária SINTÉTICA para testes automatizados.

ATENÇÃO: estes números NÃO são dados da NASA. Imitam grosseiramente um clima de Cerrado
(chuvas out–mar, seca jun–set) só para exercitar o código sem acesso à internet.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta

from app.power.client import DailySeries


def synthetic_payload(year: int, seed: int = 0, fill_every: int = 0) -> dict:
    rnd = random.Random(year * 31 + seed)
    params = {k: {} for k in ["T2M", "T2M_MAX", "T2M_MIN", "T2MDEW", "PRECTOTCORR", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN", "PS", "GWETROOT", "GWETTOP"]}
    d = date(year, 1, 1)
    i = 0
    while d.year == year:
        doy = d.timetuple().tm_yday
        wet_season = math.cos(2 * math.pi * (doy - 15) / 365)  # +1 em jan, -1 em jul
        p_rain = max(0.03, 0.35 + 0.35 * wet_season)
        rain = rnd.expovariate(1 / 14) if rnd.random() < p_rain else 0.0
        tmax = 30 - 2.5 * math.cos(2 * math.pi * (doy - 280) / 365) + rnd.gauss(0, 1.5)
        tmin = 17 + 3 * wet_season + rnd.gauss(0, 1.5) - (3 if rnd.random() < 0.01 and 150 < doy < 220 else 0)
        k = d.strftime("%Y%m%d")
        vals = {
            "T2M": (tmax + tmin) / 2, "T2M_MAX": tmax, "T2M_MIN": tmin, "T2MDEW": tmin - 2 + 4 * (wet_season + 1) / 2,
            "PRECTOTCORR": rain, "RH2M": 55 + 20 * wet_season, "WS2M": 2.0 + rnd.random(),
            "ALLSKY_SFC_SW_DWN": 19 + 3 * wet_season * -1 + rnd.gauss(0, 2), "PS": 91.5,
            "GWETROOT": 0.55 + 0.2 * wet_season, "GWETTOP": 0.5 + 0.25 * wet_season,
        }
        for p in params:
            v = round(vals[p], 2)
            if fill_every and i % fill_every == 0 and p == "PRECTOTCORR":
                v = -999
            params[p][k] = v
        d += timedelta(days=1)
        i += 1
    meta = {p: {"units": "MJ/m^2/day" if p == "ALLSKY_SFC_SW_DWN" else "C", "longname": p} for p in params}
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-48.2772, -18.9186, 870.0]},
        "properties": {"parameter": params},
        "header": {"title": "SYNTHETIC TEST DATA", "api": {"version": "test"}, "fill_value": -999},
        "messages": [],
        "parameters": meta,
    }


def synthetic_series(y0: int = 2005, y1: int = 2025) -> DailySeries:
    from app.power.client import normalize_year_payload

    dates, values, units = [], {}, {}
    for y in range(y0, y1 + 1):
        n = normalize_year_payload(synthetic_payload(y), y)
        before = len(dates)
        dates.extend(n["dates"])
        for c, col in n["values"].items():
            values.setdefault(c, [None] * before).extend(col)
        units.update(n["units"])
    return DailySeries(latitude=-18.9186, longitude=-48.2772, dates=dates, values=values, units=units,
                       longnames={c: c for c in values}, api_version="test", elevation_m=870.0, fetched_at="synthetic")
