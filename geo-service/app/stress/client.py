"""Estresse observado por satélite: MODIS LST (MOD11A2, 1 km) e MODIS ET/PET (MOD16A3GF, 500 m).

As duas partes são independentes: se uma falhar, a resposta traz a outra e ``null`` no lugar.
Só falha (HTTP 502) quando nenhuma das duas pôde ser calculada.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import ET_CITATION, LST_CITATION, Settings
from app.config import settings as default_settings
from app.planetary import Planetary, PlanetaryError
from app.stress.indicators import summarize_et, summarize_lst

LST = "modis-11A2-061"
ET = "modis-16A3GF-061"
TERRA = {"platform": {"eq": "terra"}}


class StressError(RuntimeError):
    """Nenhum indicador de estresse por satélite pôde ser obtido."""


class StressClient:
    def __init__(self, cfg: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.cfg = cfg or default_settings
        self.transport = transport

    async def _lst(self, pc: Planetary, lat: float, lon: float, today: date) -> dict[str, Any]:
        start = date(today.year - self.cfg.lst_years, today.month, 1)
        items = await pc.search(LST, lat, lon, start, today + timedelta(days=1), query=TERRA)
        vals, _ = await pc.points(LST, [i["id"] for i in items], lat, lon, ("LST_Day_1km", "QC_Day"))
        obs = [{"date": it["date"], "lst_raw": vals[it["id"]][0], "qc": vals[it["id"]][1]} for it in items if it["id"] in vals]
        return {
            "dataset": "MODIS MOD11A2 v061 (LST diurna)", "resolution_m": 1000, "composite_days": 8,
            "source_note": "Temperatura da superfície por volta das 10h30 (passagem do Terra), média de 8 dias sem nuvem, "
                           "pixel de 1 km: inclui a vizinhança do talhão.",
            "citation": LST_CITATION,
            **summarize_lst(obs, today),
        }

    async def _et(self, pc: Planetary, lat: float, lon: float, today: date) -> dict[str, Any]:
        items = await pc.search(ET, lat, lon, date(today.year - self.cfg.et_years - 1, 1, 1), today, query=TERRA)
        vals, _ = await pc.points(ET, [i["id"] for i in items], lat, lon, ("ET_500m", "PET_500m"))
        obs = [{"year": int(it["start"][:4]), "et_raw": vals[it["id"]][0], "pet_raw": vals[it["id"]][1]} for it in items if it["id"] in vals]
        return {
            "dataset": "MODIS MOD16A3GF v061 (ET/PET anual)", "resolution_m": 500,
            "source_note": "Evapotranspiração real e potencial do ano, modelo Penman-Monteith do MODIS com lacunas preenchidas, "
                           "pixel de 500 m.",
            "citation": ET_CITATION,
            **summarize_et(obs[-self.cfg.et_years:]),
        }

    async def fetch(self, lat: float, lon: float, today: date | None = None) -> dict[str, Any]:
        today = today or date.today()
        async with httpx.AsyncClient(timeout=self.cfg.pc_timeout, transport=self.transport) as http:
            pc = Planetary(self.cfg, http)
            results = await asyncio.gather(self._lst(pc, lat, lon, today), self._et(pc, lat, lon, today), return_exceptions=True)
        errors = [e for e in results if isinstance(e, BaseException)]
        for e in errors:
            if not isinstance(e, (PlanetaryError, ValueError)):
                raise e
        lst, et = (None if isinstance(x, BaseException) else x for x in results)
        if lst is None and et is None:
            raise StressError("; ".join(str(e) for e in errors) or "Sem dados de estresse por satélite.")
        return {
            "lst": lst,
            "et": et,
            "notes": [str(e) for e in errors],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
