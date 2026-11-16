"""Cliente de elevação SRTM (OpenTopoData) com cache em disco e novas tentativas."""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import SRTM_CITATION, Settings
from app.config import settings as default_settings
from app.terrain.slope import sample_grid, summarize


class TerrainError(RuntimeError):
    """Falha ao obter a elevação (rede, limite da API ou dado ausente)."""


class TerrainClient:
    def __init__(self, cfg: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.cfg = cfg or default_settings
        self.transport = transport
        self.cache_dir = Path(self.cfg.cache_dir) / "terrain"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def _elevations(self, points: list[tuple[float, float]]) -> list[float | None]:
        locations = "|".join(f"{la:.6f},{lo:.6f}" for la, lo in points)
        path = self.cache_dir / f"{hashlib.sha1(locations.encode()).hexdigest()}.json"
        if path.exists():
            return json.loads(path.read_text())["elevations"]

        delay = 1.5
        async with httpx.AsyncClient(timeout=self.cfg.terrain_timeout, transport=self.transport) as http:
            for attempt in range(4):
                try:
                    resp = await http.get(self.cfg.terrain_base_url, params={"locations": locations})
                except httpx.HTTPError as exc:
                    if attempt == 3:
                        raise TerrainError(f"Não foi possível consultar a elevação SRTM ({exc.__class__.__name__}).") from exc
                    await asyncio.sleep(delay + random.random())
                    delay *= 2
                    continue
                if resp.status_code == 200:
                    body = resp.json()
                    if body.get("status") != "OK":
                        raise TerrainError(f"Serviço de elevação respondeu: {body.get('error') or body.get('status')}")
                    elevations = [r.get("elevation") for r in body.get("results", [])]
                    if len(elevations) != len(points):
                        raise TerrainError("Resposta de elevação incompleta.")
                    path.write_text(json.dumps({"elevations": elevations, "fetched_at": datetime.now(timezone.utc).isoformat()}))
                    return elevations
                if resp.status_code in (429,) or resp.status_code >= 500:
                    if attempt < 3:
                        await asyncio.sleep(delay + random.random())
                        delay *= 2
                        continue
                raise TerrainError(f"Serviço de elevação respondeu HTTP {resp.status_code}.")
        raise TerrainError("Serviço de elevação não respondeu após várias tentativas.")

    async def fetch(self, lat: float, lon: float, boundary: dict[str, Any] | None = None) -> dict[str, Any]:
        grid = sample_grid(lat, lon, boundary)
        flat_pts = [p for row in grid["points"] for p in row]
        elev = await self._elevations(flat_pts)
        n = len(grid["points"])
        z = [elev[i * n:(i + 1) * n] for i in range(n)]
        try:
            summary = summarize(z, grid["dx_m"], grid["dy_m"])
        except ValueError as exc:
            raise TerrainError(str(exc)) from exc
        return {
            "dataset": "SRTM GL1",
            "resolution_m": 30,
            "source_note": "Elevação do radar do ônibus espacial (2000). Representa o terreno sem vegetação densa; "
                           "terraços e curvas de nível recentes não aparecem.",
            "citation": SRTM_CITATION,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            **summary,
        }
