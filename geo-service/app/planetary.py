"""Acesso aos produtos da NASA espelhados no Microsoft Planetary Computer (público, sem chave).

- ``search``: busca STAC das imagens que cobrem um ponto num período.
- ``points``: lê o valor do pixel no ponto em várias imagens (TiTiler), em paralelo e com cache em disco.

Usado pelo NDVI (MODIS MOD13Q1 e HLS 30 m), pela temperatura da superfície (MODIS LST)
e pela evapotranspiração (MODIS ET/PET).
"""

from __future__ import annotations

import asyncio
import json
import random
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings


class PlanetaryError(RuntimeError):
    """Falha ao consultar o Planetary Computer (rede, catálogo vazio ou leituras demais com erro)."""


class Planetary:
    def __init__(self, cfg: Settings, http: httpx.AsyncClient):
        self.cfg = cfg
        self.http = http
        self.cache_dir = Path(cfg.cache_dir) / "planetary"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def _request(self, method: str, url: str, **kw: Any) -> httpx.Response:
        delay = 1.0
        for attempt in range(3):
            try:
                resp = await self.http.request(method, url, **kw)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise PlanetaryError(f"Sem resposta do Planetary Computer ({exc.__class__.__name__}).") from exc
            else:
                if resp.status_code < 500 and resp.status_code != 429:
                    return resp
                if attempt == 2:
                    raise PlanetaryError(f"Planetary Computer respondeu HTTP {resp.status_code}.")
            await asyncio.sleep(delay + random.random() * 0.5)
            delay *= 2
        raise PlanetaryError("Planetary Computer não respondeu.")  # pragma: no cover

    async def search(self, collection: str, lat: float, lon: float, start: date, end: date,
                     query: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Itens STAC simplificados: ``id``, ``date`` (meio do período), ``platform``, ``start``."""
        body: dict[str, Any] = {
            "collections": [collection],
            "intersects": {"type": "Point", "coordinates": [lon, lat]},
            "datetime": f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z",
            "limit": 500,
        }
        if query:
            body["query"] = query
        url = f"{self.cfg.pc_stac_url}/search"
        feats: list[dict[str, Any]] = []
        for _ in range(10):
            resp = await self._request("POST", url, json=body)
            if resp.status_code != 200:
                raise PlanetaryError(f"Catálogo {collection} respondeu HTTP {resp.status_code}.")
            page = resp.json()
            feats.extend(page.get("features", []))
            nxt = next((l for l in page.get("links", []) if l.get("rel") == "next"), None)
            if not nxt:
                break
            url, body = nxt["href"], nxt.get("body", body)

        out: dict[tuple[str, str], dict[str, Any]] = {}
        for f in feats:
            p = f.get("properties", {})
            s = (p.get("start_datetime") or p.get("datetime") or "")[:10]
            e = (p.get("end_datetime") or p.get("datetime") or "")[:10]
            if not s or not e:
                continue
            d0, d1 = date.fromisoformat(s), date.fromisoformat(e)
            key = (p.get("platform", ""), s)
            # Mesma data e satélite (composição reprocessada ou bordas de tiles): fica um só (id maior).
            if key not in out or f["id"] > out[key]["id"]:
                out[key] = {"id": f["id"], "date": (d0 + (d1 - d0) / 2).isoformat(), "start": s, "platform": key[0]}
        return sorted(out.values(), key=lambda x: x["date"])

    async def points(self, collection: str, items: list[str], lat: float, lon: float,
                     assets: tuple[str, ...] | list[str]) -> tuple[dict[str, list[float | None]], int]:
        """Valores dos ``assets`` no pixel do ponto para cada item. Devolve (valores por id, falhas)."""
        cache_path = self.cache_dir / f"{collection}_{lat:.4f}_{lon:.4f}.json"
        cache: dict[str, list[float | None]] = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        missing = [i for i in items if i not in cache]
        sem = asyncio.Semaphore(self.cfg.pc_concurrency)

        async def one(item: str) -> list[float | None] | None:
            params = [("collection", collection), ("item", item)] + [("assets", a) for a in assets]
            async with sem:
                try:
                    resp = await self._request("GET", f"{self.cfg.pc_data_url}/item/point/{lon},{lat}", params=params)
                except PlanetaryError:
                    return None
            if resp.status_code != 200:
                return None
            vals = resp.json().get("values") or []
            return list(vals) if len(vals) >= len(assets) else None

        results = await asyncio.gather(*(one(i) for i in missing))
        failed = 0
        for item, val in zip(missing, results):
            if val is None:
                failed += 1
            else:
                cache[item] = val
        if missing:
            cache_path.write_text(json.dumps(cache))
        if items and failed > len(items) / 2:
            raise PlanetaryError(f"{collection}: {failed} de {len(items)} leituras falharam.")
        return {i: cache[i] for i in items if i in cache}, failed
