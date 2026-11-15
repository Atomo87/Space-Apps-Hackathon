"""Cobertura verde do talhão por satélite, pelo Microsoft Planetary Computer.

- MODIS MOD13Q1/MYD13Q1 v061: NDVI de 250 m a cada 16 dias, últimos ``ndvi_years`` anos (série longa, obrigatória).
- HLS v2.0 (Landsat 8/9 + Sentinel-2, harmonizado pela NASA): NDVI de 30 m, últimos ``hls_years`` anos
  (escala do talhão, opcional — se falhar, a resposta segue só com o MODIS).
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import HLS_CITATION, MODIS_CITATION, Settings
from app.config import settings as default_settings
from app.planetary import Planetary, PlanetaryError
from app.vegetation.ndvi import summarize

MODIS = "modis-13Q1-061"
MODIS_ASSETS = ("250m_16_days_NDVI", "250m_16_days_pixel_reliability")
# HLS: vermelho e infravermelho próximo equivalentes nos dois sensores + máscara de nuvem.
HLS = {"hls2-s30": ("B04", "B8A", "Fmask"), "hls2-l30": ("B04", "B05", "Fmask")}
# Fmask: bit 1 nuvem, 2 vizinho de nuvem/sombra, 3 sombra, 4 neve, 5 água.
FMASK_REJECT = 0b111110


class VegetationError(RuntimeError):
    """Falha ao obter o NDVI (rede, catálogo sem imagens ou nuvens demais)."""


def hls_ndvi(red: float | None, nir: float | None, fmask: float | None) -> int | None:
    """NDVI ×10 000 de um pixel HLS limpo; None se nuvem, sombra, água ou sem dado."""
    if red is None or nir is None or red <= 0 or nir <= 0 or red > 10000 or nir > 10000:
        return None
    if fmask is not None and int(fmask) & FMASK_REJECT:
        return None
    return round((nir - red) / (nir + red) * 10000)


class NdviClient:
    def __init__(self, cfg: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.cfg = cfg or default_settings
        self.transport = transport

    async def _modis(self, pc: Planetary, lat: float, lon: float, today: date) -> tuple[list[dict[str, Any]], int]:
        start = date(today.year - self.cfg.ndvi_years, today.month, 1)
        items = await pc.search(MODIS, lat, lon, start, today + timedelta(days=1))
        if not items:
            raise VegetationError("Nenhuma imagem MODIS encontrada para este ponto.")
        vals, failed = await pc.points(MODIS, [i["id"] for i in items], lat, lon, MODIS_ASSETS)
        obs = [
            {"date": it["date"], "platform": it["platform"], "ndvi_raw": vals[it["id"]][0],
             "reliability": -1 if vals[it["id"]][1] is None else int(vals[it["id"]][1])}
            for it in items if it["id"] in vals
        ]
        return obs, failed

    async def _hls(self, pc: Planetary, lat: float, lon: float, today: date) -> dict[str, Any] | None:
        start = today - timedelta(days=365 * self.cfg.hls_years)
        obs: list[dict[str, Any]] = []
        for col, assets in HLS.items():
            items = await pc.search(col, lat, lon, start, today + timedelta(days=1), query={"eo:cloud_cover": {"lt": 60}})
            vals, _ = await pc.points(col, [i["id"] for i in items], lat, lon, assets)
            for it in items:
                v = vals.get(it["id"])
                if v:
                    nd = hls_ndvi(v[0], v[1], v[2])
                    obs.append({"date": it["date"], "platform": "Sentinel-2" if col.endswith("s30") else "Landsat",
                                "ndvi_raw": nd, "reliability": 0 if nd is not None else 3})
        summary = summarize(obs, today)
        return {
            "dataset": "HLS v2.0 (HLSL30 + HLSS30)",
            "resolution_m": 30,
            "source_note": "NDVI de 30 m no centro do talhão (Landsat 8/9 e Sentinel-2 harmonizados pela NASA). "
                           "Imagens com nuvem, sombra ou água são descartadas pela máscara Fmask.",
            "citation": HLS_CITATION,
            **summary,
        }

    async def fetch(self, lat: float, lon: float, today: date | None = None) -> dict[str, Any]:
        today = today or date.today()
        async with httpx.AsyncClient(timeout=self.cfg.pc_timeout, transport=self.transport) as http:
            pc = Planetary(self.cfg, http)

            async def hls_or_none() -> dict[str, Any] | None:
                if self.cfg.hls_years <= 0:
                    return None
                try:
                    return await self._hls(pc, lat, lon, today)
                except (PlanetaryError, ValueError):
                    return None  # complementar: segue só com o MODIS

            try:
                (obs, failed), hls = await asyncio.gather(self._modis(pc, lat, lon, today), hls_or_none())
            except PlanetaryError as exc:
                raise VegetationError(str(exc)) from exc

        try:
            summary = summarize(obs, today)
        except ValueError as exc:
            raise VegetationError(str(exc)) from exc
        return {
            "dataset": "MODIS MOD13Q1/MYD13Q1 v061",
            "resolution_m": 250,
            "composite_days": 16,
            "source_note": "NDVI do pixel de 250 m que contém o centro do talhão. Só entram composições com "
                           "confiabilidade boa ou marginal (sem nuvem, sem neve).",
            "citation": MODIS_CITATION,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "failed_requests": failed,
            **summary,
            "hls": hls,
        }
