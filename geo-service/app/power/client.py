"""Cliente da NASA POWER (API diária por ponto) — tarefa B2.

Regras do doc 10:
- consultas anuais, cache pela consulta normalizada completa;
- ``fill_value`` → ``None`` (nunca zero); séries alinhadas pela data;
- 422 → corrigir parâmetros (aqui: refazer sem os opcionais), sem repetição cega;
- 429 → respeitar Retry-After, com espera crescente e jitter; 5xx/rede → tentativas limitadas;
- guardar versão da API, mensagens, unidades e instante da coleta.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings, settings as default_settings


class PowerError(RuntimeError):
    """Falha ao obter dados da NASA POWER (mensagem já em português)."""


class PowerParameterRejected(PowerError):
    """HTTP 422: a API recusou a consulta (parâmetro inválido)."""


@dataclass
class DailySeries:
    latitude: float
    longitude: float
    dates: list[date]
    values: dict[str, list[float | None]]
    units: dict[str, str]
    longnames: dict[str, str]
    api_version: str | None = None
    messages: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    fetched_at: str = ""
    elevation_m: float | None = None
    requests: int = 0
    cache_hits: int = 0

    def get(self, code: str) -> list[float | None]:
        return self.values.get(code, [None] * len(self.dates))

    def has(self, code: str) -> bool:
        return code in self.values and any(v is not None for v in self.values[code])


def normalize_year_payload(payload: dict[str, Any], year: int) -> dict[str, Any]:
    """Converte a resposta JSON de um ano em séries alinhadas pela data, com fill_value → None."""
    header = payload.get("header") or {}
    fill = header.get("fill_value", -999)
    params = (payload.get("properties") or {}).get("parameter") or {}
    if not params:
        raise PowerError("Resposta da NASA POWER sem 'properties.parameter'.")

    start = date(year, 1, 1)
    days = (date(year, 12, 31) - start).days + 1
    dates = [start + timedelta(days=i) for i in range(days)]
    keys = [d.strftime("%Y%m%d") for d in dates]

    values: dict[str, list[float | None]] = {}
    for code, series in params.items():
        col: list[float | None] = []
        for k in keys:
            v = series.get(k)
            if v is None:
                col.append(None)
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                col.append(None)
                continue
            if fill is not None and abs(fv - float(fill)) < 1e-6:
                col.append(None)
            else:
                col.append(fv)
        values[code] = col

    meta = payload.get("parameters") or {}
    coords = (payload.get("geometry") or {}).get("coordinates") or []
    return {
        "dates": dates,
        "values": values,
        "units": {c: (meta.get(c) or {}).get("units", "") for c in values},
        "longnames": {c: (meta.get(c) or {}).get("longname", "") for c in values},
        "api_version": ((header.get("api") or {}).get("version")) if isinstance(header.get("api"), dict) else None,
        "messages": [str(m) for m in (payload.get("messages") or [])],
        "elevation_m": float(coords[2]) if len(coords) >= 3 and coords[2] is not None else None,
    }


class PowerClient:
    def __init__(self, cfg: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.cfg = cfg or default_settings
        self.transport = transport
        self.cache_dir = Path(self.cfg.cache_dir) / "power"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ---------- cache ----------
    def _query(self, lat: float, lon: float, year: int, params: list[str]) -> dict[str, str]:
        return {
            "latitude": f"{lat:.4f}",
            "longitude": f"{lon:.4f}",
            "start": f"{year}0101",
            "end": f"{year}1231",
            "community": self.cfg.community,
            "parameters": ",".join(sorted(params)),
            "format": "json",
            "units": "metric",
            "time-standard": self.cfg.time_standard,
        }

    def _cache_path(self, query: dict[str, str]) -> Path:
        key = hashlib.sha1(json.dumps(query, sort_keys=True).encode()).hexdigest()
        return self.cache_dir / f"{key}.json"

    # ---------- HTTP ----------
    async def _get_year(self, http: httpx.AsyncClient, lat: float, lon: float, year: int, params: list[str]) -> tuple[dict, bool]:
        query = self._query(lat, lon, year, params)
        path = self._cache_path(query)
        if path.exists():
            return json.loads(path.read_text()), True

        url = f"{self.cfg.power_base_url}/api/temporal/daily/point"
        delay = 2.0
        for attempt in range(4):
            try:
                resp = await http.get(url, params=query)
            except httpx.HTTPError as exc:
                if attempt == 3:
                    raise PowerError(f"Não foi possível conectar à NASA POWER ({exc.__class__.__name__}).") from exc
                await asyncio.sleep(delay + random.random())
                delay *= 2
                continue

            if resp.status_code == 200:
                payload = resp.json()
                envelope = {"query": query, "fetched_at": datetime.now(timezone.utc).isoformat(), "payload": payload}
                path.write_text(json.dumps(envelope))
                return envelope, False
            if resp.status_code == 422:
                raise PowerParameterRejected(f"A NASA POWER recusou a consulta (422): {resp.text[:300]}")
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else delay
                await asyncio.sleep(wait + random.random())
                delay *= 2
                continue
            if resp.status_code >= 500 and attempt < 3:
                await asyncio.sleep(delay + random.random())
                delay *= 2
                continue
            raise PowerError(f"A NASA POWER respondeu HTTP {resp.status_code}.")
        raise PowerError("A NASA POWER não respondeu após várias tentativas.")

    async def fetch(self, lat: float, lon: float, start_year: int | None = None, end_year: int | None = None) -> DailySeries:
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise PowerError("Coordenadas fora do intervalo válido.")
        y0 = start_year or self.cfg.start_year
        y1 = end_year or self.cfg.end_year
        if y0 < 1981 or y1 < y0:
            raise PowerError("Período inválido: a série diária da POWER começa em 1981.")

        params = list(self.cfg.core_parameters) + list(self.cfg.optional_parameters)
        missing_optional: list[str] = []
        sem = asyncio.Semaphore(max(1, self.cfg.power_concurrency))

        async with httpx.AsyncClient(timeout=self.cfg.power_timeout, transport=self.transport) as http:
            # Primeiro ano sozinho: descobre se os parâmetros opcionais são aceitos.
            try:
                first, hit0 = await self._get_year(http, lat, lon, y0, params)
            except PowerParameterRejected:
                missing_optional = list(self.cfg.optional_parameters)
                params = list(self.cfg.core_parameters)
                first, hit0 = await self._get_year(http, lat, lon, y0, params)

            async def one(year: int):
                async with sem:
                    return await self._get_year(http, lat, lon, year, params)

            rest = await asyncio.gather(*(one(y) for y in range(y0 + 1, y1 + 1)))

        envelopes = [(first, hit0), *rest]
        dates: list[date] = []
        values: dict[str, list[float | None]] = {}
        units: dict[str, str] = {}
        longnames: dict[str, str] = {}
        messages: list[str] = []
        api_version = None
        elevation = None
        fetched = []
        for (env, _hit), year in zip(envelopes, range(y0, y1 + 1)):
            norm = normalize_year_payload(env["payload"], year)
            n_before = len(dates)
            dates.extend(norm["dates"])
            for code in set(values) | set(norm["values"]):
                col = values.setdefault(code, [None] * n_before)
                col.extend(norm["values"].get(code, [None] * len(norm["dates"])))
            units.update({k: v for k, v in norm["units"].items() if v})
            longnames.update({k: v for k, v in norm["longnames"].items() if v})
            messages.extend(m for m in norm["messages"] if m not in messages)
            api_version = norm["api_version"] or api_version
            elevation = norm["elevation_m"] if norm["elevation_m"] is not None else elevation
            fetched.append(env.get("fetched_at", ""))

        # Opcionais que vieram vazios também são lacuna.
        for code in self.cfg.optional_parameters:
            if code not in missing_optional and not any(v is not None for v in values.get(code, [])):
                missing_optional.append(code)

        return DailySeries(
            latitude=lat,
            longitude=lon,
            dates=dates,
            values=values,
            units=units,
            longnames=longnames,
            api_version=api_version,
            messages=messages,
            missing_optional=missing_optional,
            fetched_at=max(fetched) if fetched else "",
            elevation_m=elevation,
            requests=len(envelopes),
            cache_hits=sum(1 for _, h in envelopes if h),
        )
