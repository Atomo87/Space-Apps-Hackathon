"""geo-service do GeoSafra (frente B) — API HTTP consumida pelo Laravel.

Rotas:
  GET  /health                 → vivo? (também usado pelo ping que evita o "sono" no Render)
  GET  /v1/catalog             → culturas, pragas, equipamentos e modelos de rotação
  POST /v1/climate-profile     → consulta a NASA POWER e devolve o ClimateProfile (lento: 10–90 s sem cache)
  POST /v1/terrain             → declividade e fator LS do talhão pela elevação SRTM (~30 m)
  POST /v1/vegetation          → NDVI MODIS (250 m, 5 anos) + HLS (30 m, 2 anos): cobertura verde do talhão
  POST /v1/stress              → MODIS LST (temperatura da superfície) + MODIS ET/PET (estresse evaporativo)
  POST /v1/earthdata           → SMAP, GPM IMERG, ECOSTRESS e GRACE-FO (exige EARTHDATA_TOKEN)
  POST /v1/analysis         → diagnóstico + estratégias A–D a partir do ClimateProfile guardado (rápido)
"""

from __future__ import annotations

import time

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.catalog.loader import load_catalog
from app.climate.indicators import build_climate_profile
from app.config import ENGINE_VERSION, settings
from app.engine.engine import run
from app.i18n import analysis_locale, localize_metadata, tr
from app.power.client import PowerClient, PowerError
from app.schemas import AnalysisRequest, ClimateRequest, TerrainRequest, VegetationRequest
from app.terrain.client import TerrainClient, TerrainError
from app.earthdata.client import EarthdataClient, EarthdataError
from app.stress.client import StressClient, StressError
from app.vegetation.client import NdviClient, VegetationError

app = FastAPI(title="GeoSafra geo-service", version=ENGINE_VERSION)

if settings.cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])


def problem(status: int, title: str, detail: str) -> JSONResponse:
    return JSONResponse({"type": "about:blank", "title": title, "status": status, "detail": detail},
                        status_code=status, media_type="application/problem+json")


@app.exception_handler(PowerError)
async def power_error(_: Request, exc: PowerError) -> JSONResponse:
    return problem(502, "Falha na NASA POWER", str(exc))


@app.exception_handler(TerrainError)
async def terrain_error(_: Request, exc: TerrainError) -> JSONResponse:
    return problem(502, "Falha na elevação SRTM", str(exc))


@app.exception_handler(VegetationError)
async def vegetation_error(_: Request, exc: VegetationError) -> JSONResponse:
    return problem(502, "Falha no NDVI MODIS", str(exc))


@app.exception_handler(StressError)
async def stress_error(_: Request, exc: StressError) -> JSONResponse:
    return problem(502, "Falha no estresse por satélite", str(exc))


@app.exception_handler(EarthdataError)
async def earthdata_error(_: Request, exc: EarthdataError) -> JSONResponse:
    return problem(502, "Falha nos dados NASA Earthdata", str(exc))


@app.exception_handler(KeyError)
async def key_error(_: Request, exc: KeyError) -> JSONResponse:
    return problem(422, "Dado inválido", str(exc).strip("'\""))


def check_token(x_geosafra_token: str | None = Header(default=None)) -> None:
    if settings.api_token and x_geosafra_token != settings.api_token:
        raise HTTPException(status_code=401, detail="Token inválido.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "engine_version": ENGINE_VERSION, "catalog_version": load_catalog().version}


@app.get("/v1/catalog", dependencies=[Depends(check_token)])
def catalog() -> dict:
    return load_catalog().public()


@app.post("/v1/climate-profile", dependencies=[Depends(check_token)])
async def climate_profile(req: ClimateRequest) -> dict:
    t0 = time.perf_counter()
    series = await PowerClient().fetch(req.latitude, req.longitude, req.start_year, req.end_year)
    profile = build_climate_profile(series)
    profile["source"]["processing_seconds"] = round(time.perf_counter() - t0, 1)
    profile["engine_version"] = ENGINE_VERSION
    return profile


@app.post("/v1/terrain", dependencies=[Depends(check_token)])
async def terrain(req: TerrainRequest) -> dict:
    return await TerrainClient().fetch(req.latitude, req.longitude, req.boundary)


@app.post("/v1/vegetation", dependencies=[Depends(check_token)])
async def vegetation(req: VegetationRequest) -> dict:
    t0 = time.perf_counter()
    out = await NdviClient().fetch(req.latitude, req.longitude)
    out["processing_seconds"] = round(time.perf_counter() - t0, 1)
    return out


@app.post("/v1/stress", dependencies=[Depends(check_token)])
async def stress(req: VegetationRequest) -> dict:
    t0 = time.perf_counter()
    out = await StressClient().fetch(req.latitude, req.longitude)
    out["processing_seconds"] = round(time.perf_counter() - t0, 1)
    return out


@app.post("/v1/earthdata", dependencies=[Depends(check_token)])
async def earthdata(req: VegetationRequest) -> dict:
    t0 = time.perf_counter()
    out = await EarthdataClient().fetch(req.latitude, req.longitude)
    out["processing_seconds"] = round(time.perf_counter() - t0, 1)
    return out


@app.post("/v1/analysis", dependencies=[Depends(check_token)])
def analysis(req: AnalysisRequest, accept_language: str | None = Header(default=None)) -> dict:
    with analysis_locale(accept_language):
        if not req.climate.get("monthly"):
            raise HTTPException(status_code=422, detail=tr("ClimateProfile ausente ou inválido."))
        unknown = [h.crop for h in req.history if h.crop not in load_catalog().crops]
        if unknown:
            raise HTTPException(status_code=422, detail=tr("Culturas fora do catálogo: {0}", ", ".join(unknown)))
        return localize_metadata(run(req))
