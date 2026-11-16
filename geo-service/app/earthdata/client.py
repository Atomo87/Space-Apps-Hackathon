"""Conjuntos da NASA que exigem login Earthdata (token de serviço em EARTHDATA_TOKEN).

| Conjunto  | Produto            | Acesso                                                       |
|-----------|--------------------|--------------------------------------------------------------|
| SMAP      | SPL3SMP_E (9 km)   | OPeNDAP Earthdata Cloud: recorte 3×3 pixels por dia amostrado |
| GPM       | GPM_3IMERGM (0,1°) | OPeNDAP Earthdata Cloud: recorte 1 pixel por mês              |
| ECOSTRESS | ECO_L4T_ESI (70 m) | COG no LP DAAC: leitura de 1 pixel (URL assinada + GDAL)      |
| GRACE-FO  | Mascon JPL CRI v04 | arquivo único (~46 MB) baixado uma vez e lido com h5py        |

Cada conjunto é independente: o que falhar vira ``null`` e uma nota; só há erro se todos falharem.
Os valores lidos ficam em cache em disco por arquivo da NASA (reprocessar só busca o que é novo).
"""

from __future__ import annotations

import asyncio
import calendar
import io
import json
import math
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.config import ECOSTRESS_CITATION, GPM_CITATION, GRACE_CITATION, SMAP_CITATION, Settings
from app.config import settings as default_settings
from app.earthdata.indicators import summarize_ecostress, summarize_gpm, summarize_grace, summarize_smap

CMR = "https://cmr.earthdata.nasa.gov/search"
OPENDAP = "https://opendap.earthdata.nasa.gov/collections"
# EASE-Grid 2.0 global, 9 km (EPSG:6933)
EASE_X0, EASE_Y0, EASE_CELL = -17367530.44516138, 7314540.830638504, 9008.055210146


class EarthdataError(RuntimeError):
    """Nenhum conjunto Earthdata pôde ser obtido (ou falta o token)."""


def ease2_rowcol(lat: float, lon: float) -> tuple[int, int]:
    """Linha/coluna da grade EASE-Grid 2.0 global de 9 km (projeção cilíndrica de área igual, elipsoide WGS84)."""
    a, e2 = 6378137.0, 0.0066943799901413165
    e = math.sqrt(e2)
    lat0 = math.radians(30.0)
    k0 = math.cos(lat0) / math.sqrt(1 - e2 * math.sin(lat0) ** 2)

    def q(phi: float) -> float:
        s = math.sin(phi)
        return (1 - e2) * (s / (1 - e2 * s * s) - math.log((1 - e * s) / (1 + e * s)) / (2 * e))

    x = a * k0 * math.radians(lon)
    y = a * q(math.radians(lat)) / (2 * k0)
    return int((EASE_Y0 - y) // EASE_CELL), int((x - EASE_X0) // EASE_CELL)


def friendly(exc: BaseException) -> str:
    msg = str(exc)
    if "EULA" in msg:
        return ("Falta aceitar o termo de uso (EULA) da GES DISC na sua conta Earthdata: entre em urs.earthdata.nasa.gov › "
                "Applications › Authorized Apps e autorize “NASA GESDISC DATA ARCHIVE”.")
    return msg


class EarthdataClient:
    def __init__(self, cfg: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.cfg = cfg or default_settings
        self.transport = transport
        self.cache_dir = Path(self.cfg.cache_dir) / "earthdata"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.auth = {"Authorization": f"Bearer {self.cfg.earthdata_token}"}

    # ---------------------------------------------------------------- utilidades
    def _cache(self, name: str) -> tuple[Path, dict[str, Any]]:
        p = self.cache_dir / f"{name}.json"
        return p, (json.loads(p.read_text()) if p.exists() else {})

    async def _granules(self, http: httpx.AsyncClient, short_name: str, start: date, end: date, point: tuple[float, float] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"short_name": short_name, "temporal": f"{start.isoformat()}T00:00:00Z,{end.isoformat()}T23:59:59Z",
                                  "page_size": 2000, "sort_key": "start_date"}
        if point:
            params["point"] = f"{point[1]},{point[0]}"
        out: list[dict[str, Any]] = []
        headers: dict[str, str] = {}
        for _ in range(10):
            r = await http.get(f"{CMR}/granules.json", params=params, headers=headers)
            if r.status_code != 200:
                raise EarthdataError(f"CMR respondeu HTTP {r.status_code} para {short_name}.")
            out.extend(r.json()["feed"]["entry"])
            after = r.headers.get("CMR-Search-After")
            if not after or len(r.json()["feed"]["entry"]) < 2000:
                break
            headers = {"CMR-Search-After": after}
        return out

    async def _get(self, http: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None, **kw: Any) -> httpx.Response:
        for attempt in range(3):
            try:
                r = await http.get(url, headers={**self.auth, **(headers or {})}, follow_redirects=True, **kw)
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise EarthdataError(f"Sem resposta da NASA ({exc.__class__.__name__}).") from exc
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            if r.status_code in (401, 403):
                raise EarthdataError(r.text[:300])
            if r.status_code >= 500 and attempt < 2:
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            return r
        raise EarthdataError("NASA não respondeu.")  # pragma: no cover

    async def _opendap_nc4(self, http: httpx.AsyncClient, collection: str, granule: str, ce: str) -> dict[str, Any]:
        import h5py

        r = await self._get(http, f"{OPENDAP}/{collection}/granules/{granule}.dap.nc4", params={"dap4.ce": ce})
        # O OPeNDAP às vezes devolve o erro do arquivo de origem (ex.: EULA, 403) no corpo, sem netCDF.
        if r.status_code != 200 or not r.content.startswith(b"\x89HDF"):
            raise EarthdataError(f"OPeNDAP HTTP {r.status_code}: {r.text[:300]}")

        out: dict[str, Any] = {}
        with h5py.File(io.BytesIO(r.content), "r") as f:
            f.visititems(lambda name, obj: out.__setitem__(name, obj[()]) if isinstance(obj, h5py.Dataset) else None)
        return out

    # ---------------------------------------------------------------- SMAP
    async def smap(self, http: httpx.AsyncClient, lat: float, lon: float, today: date) -> dict[str, Any]:
        row, col = ease2_rowcol(lat, lon)
        grans = await self._granules(http, "SPL3SMP_E", today - timedelta(days=365 * self.cfg.smap_years), today)
        picked, last = [], None
        for g in grans:
            d = date.fromisoformat(g["time_start"][:10])
            if last is None or (d - last).days >= self.cfg.smap_step_days:
                picked.append((d, g))
                last = d
        path, cache = self._cache(f"smap_{row}_{col}")
        win = f"[{row - 1}:1:{row + 1}][{col - 1}:1:{col + 1}]"
        ce = ";".join(f"/Soil_Moisture_Retrieval_Data_{p}/{v}{win}" for p, v in
                      (("AM", "soil_moisture"), ("PM", "soil_moisture_pm"), ("AM", "retrieval_qual_flag"), ("PM", "retrieval_qual_flag_pm")))
        sem = asyncio.Semaphore(self.cfg.earthdata_concurrency)

        async def one(d: date, g: dict[str, Any]) -> None:
            if g["title"] in cache:
                return
            async with sem:
                try:
                    v = await self._opendap_nc4(http, g["collection_concept_id"], g["title"], ce)
                except EarthdataError:
                    return
            vals = []
            for sm_key, qf_key in (("Soil_Moisture_Retrieval_Data_AM/soil_moisture", "Soil_Moisture_Retrieval_Data_AM/retrieval_qual_flag"),
                                   ("Soil_Moisture_Retrieval_Data_PM/soil_moisture_pm", "Soil_Moisture_Retrieval_Data_PM/retrieval_qual_flag_pm")):
                sm, qf = v.get(sm_key), v.get(qf_key)
                if sm is None:
                    continue
                center = float(sm[1][1])
                flag = int(qf[1][1]) if qf is not None else 0
                if center > -999 and not (flag & 1):  # bit 0 = qualidade recomendada não atingida
                    vals.append(center)
            cache[g["title"]] = {"date": d.isoformat(), "sm": round(sum(vals) / len(vals), 4) if vals else None}

        await asyncio.gather(*(one(d, g) for d, g in picked))
        path.write_text(json.dumps(cache))
        obs = [cache[g["title"]] for _, g in picked if g["title"] in cache]
        return {"dataset": "SMAP SPL3SMP_E v6", "resolution_m": 9000,
                "source_note": "Umidade dos primeiros ~5 cm do solo, passagens das 6h e 18h, pixel de 9 km (inclui a vizinhança). "
                               f"Uma passagem a cada {self.cfg.smap_step_days} dias; só retornos de qualidade recomendada.",
                "citation": SMAP_CITATION, **summarize_smap(obs, today)}

    # ---------------------------------------------------------------- GPM IMERG
    async def gpm(self, http: httpx.AsyncClient, lat: float, lon: float, today: date, power_monthly: dict[int, float] | None) -> dict[str, Any]:
        grans = await self._granules(http, "GPM_3IMERGM", date(today.year - self.cfg.gpm_years, 1, 1), today)
        i_lon, i_lat = round((lon + 179.95) / 0.1), round((lat + 89.95) / 0.1)
        path, cache = self._cache(f"gpm_{i_lat}_{i_lon}")
        sem = asyncio.Semaphore(self.cfg.earthdata_concurrency)
        errors: list[str] = []

        async def one(g: dict[str, Any]) -> None:
            if g["title"] in cache or any("EULA" in e for e in errors):
                return
            async with sem:
                try:
                    v = await self._opendap_nc4(http, g["collection_concept_id"], g["title"], f"/Grid/precipitation[0][{i_lon}][{i_lat}]")
                except EarthdataError as exc:
                    errors.append(str(exc))
                    return
            # O recorte traz também variáveis auxiliares (latv, lonv, nv, time): lemos só a chuva.
            prec = v.get("Grid/precipitation")
            if prec is None:
                errors.append("Recorte do GPM sem a variável de chuva.")
                return
            rate = float(prec.ravel()[0])  # mm/h
            d = date.fromisoformat(g["time_start"][:10])
            hours = calendar.monthrange(d.year, d.month)[1] * 24
            cache[g["title"]] = {"month": d.isoformat()[:7], "mm": round(rate * hours, 1) if rate >= 0 else None}

        await asyncio.gather(*(one(g) for g in grans))
        path.write_text(json.dumps(cache))
        obs = [cache[g["title"]] for g in grans if g["title"] in cache]
        if errors and len(obs) < 24:
            # O OPeNDAP devolve uma página HTML genérica; o servidor de origem diz o motivo real (ex.: EULA não aceito).
            direct = next((l["href"] for l in grans[-1]["links"] if l["href"].startswith("https") and l["href"].endswith(".HDF5")), None) if grans else None
            if direct:
                await self._get(http, direct, headers={"Range": "bytes=0-15"})  # levanta EarthdataError com a causa
            raise EarthdataError("Leitura do GPM IMERG falhou no OPeNDAP.")
        return {"dataset": "GPM IMERG Final V07 (mensal)", "resolution_m": 11000,
                "source_note": "Chuva estimada por satélites (radar e micro-ondas) calibrada com pluviômetros, pixel de 0,1° (~11 km).",
                "citation": GPM_CITATION, **summarize_gpm(obs, power_monthly)}

    # ---------------------------------------------------------------- ECOSTRESS
    async def ecostress(self, http: httpx.AsyncClient, lat: float, lon: float, today: date) -> dict[str, Any]:
        grans = await self._granules(http, "ECO_L4T_ESI", today - timedelta(days=365 * self.cfg.ecostress_years), today, point=(lat, lon))
        seen: set[str] = set()
        picked = []
        for g in grans:  # o ponto pode cair em 2 tiles da mesma passagem: fica um
            key = g["time_start"][:16]
            if key not in seen:
                seen.add(key)
                picked.append(g)
        path, cache = self._cache(f"ecostress_{lat:.4f}_{lon:.4f}")
        os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
        sem = asyncio.Semaphore(self.cfg.earthdata_concurrency)

        def read(url: str) -> float | None:
            import rasterio
            from rasterio.warp import transform

            with rasterio.open(url) as ds:
                xs, ys = transform("EPSG:4326", ds.crs, [lon], [lat])
                v = float(list(ds.sample([(xs[0], ys[0])]))[0][0])
            return None if math.isnan(v) else v

        async def one(g: dict[str, Any]) -> None:
            if g["title"] in cache:
                return
            href = next((l["href"] for l in g["links"] if l["href"].startswith("https") and l["href"].endswith("_ESI.tif")), None)
            if not href:
                return
            async with sem:
                try:
                    r = await http.get(href, headers=self.auth, follow_redirects=False)
                    signed = r.headers.get("location", href)
                    v = await asyncio.to_thread(read, signed)
                except Exception:  # noqa: BLE001 — arquivo isolado com problema não derruba a série
                    return
            cache[g["title"]] = {"datetime": g["time_start"][:16], "esi": None if v is None else round(v, 4)}

        await asyncio.gather(*(one(g) for g in picked))
        path.write_text(json.dumps(cache))
        obs = [cache[g["title"]] for g in picked if g["title"] in cache]
        out = summarize_ecostress(obs)
        return {"dataset": "ECOSTRESS ECO_L4T_ESI v002", "resolution_m": 70,
                "source_note": f"Índice de estresse evaporativo (ET real ÷ potencial) em pixel de 70 m, na hora da passagem da "
                               f"Estação Espacial. {len(obs)} passagens lidas; nuvens deixam a maioria sem valor.",
                "citation": ECOSTRESS_CITATION, "passes": len(obs), **out}

    # ---------------------------------------------------------------- GRACE
    async def grace(self, http: httpx.AsyncClient, lat: float, lon: float) -> dict[str, Any]:
        import h5py

        e = (await http.get(f"{CMR}/granules.json", params={"short_name": "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4",
                                                              "page_size": 1, "sort_key": "-start_date"})).json()["feed"]["entry"][0]
        link = next(l["href"] for l in e["links"] if l["href"].startswith("https") and l["href"].endswith(".nc"))
        local = self.cache_dir / Path(link).name
        if not local.exists():
            for old in self.cache_dir.glob("GRCTellus.JPL.*.nc"):
                old.unlink()  # versão anterior do arquivo mensal
            r = await self._get(http, link, timeout=180)
            if r.status_code != 200:
                raise EarthdataError(f"GRACE respondeu HTTP {r.status_code}.")
            local.write_bytes(r.content)

        def read() -> list[dict[str, Any]]:
            with h5py.File(local, "r") as f:
                la, lo = f["lat"][:], f["lon"][:]
                i, j = int(abs(la - lat).argmin()), int(abs(lo - (lon % 360)).argmin())
                cm = f["lwe_thickness"][:, i, j]
                scale = float(f["scale_factor"][i, j]) if "scale_factor" in f else 1.0
                days = f["time"][:]
            base = date(2002, 1, 1)
            return [{"date": (base + timedelta(days=float(t))).isoformat(), "cm": float(v) * scale} for t, v in zip(days, cm)]

        obs = await asyncio.to_thread(read)
        return {"dataset": "GRACE/GRACE-FO JPL Mascon RL06.3 v04 CRI", "resolution_m": 300000,
                "source_note": "Variação da água total (solo, aquífero e superfície) em relação a 2004–2009, em cm de lâmina, "
                               "em blocos de ~300 km: retrata a região, não o talhão.",
                "citation": GRACE_CITATION, **summarize_grace(obs)}

    # ---------------------------------------------------------------- tudo
    async def fetch(self, lat: float, lon: float, power_monthly: dict[int, float] | None = None, today: date | None = None) -> dict[str, Any]:
        if not self.cfg.earthdata_token:
            raise EarthdataError("Token Earthdata não configurado (EARTHDATA_TOKEN).")
        today = today or date.today()
        async with httpx.AsyncClient(timeout=self.cfg.earthdata_timeout, transport=self.transport) as http:
            names = ("smap", "gpm", "ecostress", "grace")
            results = await asyncio.gather(
                self.smap(http, lat, lon, today), self.gpm(http, lat, lon, today, power_monthly),
                self.ecostress(http, lat, lon, today), self.grace(http, lat, lon), return_exceptions=True)
        out: dict[str, Any] = {}
        notes = []
        for name, res in zip(names, results):
            if isinstance(res, BaseException):
                if not isinstance(res, (EarthdataError, ValueError, httpx.HTTPError, KeyError, StopIteration, OSError)):
                    raise res
                out[name] = None
                notes.append(f"{name.upper()}: {friendly(res)}")
            else:
                out[name] = res
        if all(out[n] is None for n in names):
            raise EarthdataError("; ".join(notes))
        return {**out, "notes": notes, "fetched_at": datetime.now(timezone.utc).isoformat()}
