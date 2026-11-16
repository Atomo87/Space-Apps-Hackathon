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
from pathlib import Path
from uuid import UUID
import sqlite3

from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.exceptions import RequestValidationError
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.catalog.loader import load_catalog
from app.catalog.evidence import crop_evidence
from app.delivery import DeliveryProgress, progress
from app.climate.indicators import build_climate_profile
from app.config import ENGINE_VERSION, settings
from app.engine.engine import run
from app.power.client import PowerClient, PowerError
from app.schemas import AnalysisRequest, ClimateRequest, TerrainRequest, VegetationRequest
from app.terrain.client import TerrainClient, TerrainError
from app.earthdata.client import EarthdataClient, EarthdataError
from app.stress.client import StressClient, StressError
from app.vegetation.client import NdviClient, VegetationError
from app.insights.contracts import AnalysisResponse, ApiProblem, InsightsRequest, InsightsResponse, InsightsCapabilities
from app.insights.store import SnapshotStore
from app.insights.service import insights_for, PROMPT_VERSION
from app.insights.knowledge import Knowledge
from app.provenance import register, verify
from app.engine.cultivation import CultivationRequest, CultivationResponse, assess

app = FastAPI(title="GeoSafra geo-service", version=ENGINE_VERSION,
    description="API do motor do sênior. Fluxo: fontes → POST /v1/analysis → analysis_id → POST /v1/insights. "
                "Insights são apoio histórico; não preveem produtividade ou lucro. Gemini é opcional e desabilitado por padrão. "
                "O token compartilhado autentica o serviço; o Laravel deve autorizar o acesso de cada produtor às suas análises.",
    openapi_tags=[{"name":"Fontes", "description":"Consultas independentes às fontes ambientais."},
                  {"name":"Análises", "description":"Cálculo do motor e snapshots locais temporários."},
                  {"name":"Insights", "description":"Explicações por ID, RAG local e Gemini opcional, com fallback."}])
service_key = APIKeyHeader(name="X-GeoSafra-Token", auto_error=False, scheme_name="GeoSafraToken",
                          description="Token do serviço GeoSafra, quando configurado. Não é a chave Gemini nem Earthdata.")
API_ERRORS = {401:{"content":{"application/problem+json":{"schema":ApiProblem.model_json_schema()}},"description":"Token ausente ou inválido."},
              422:{"content":{"application/problem+json":{"schema":ApiProblem.model_json_schema()}},"description":"Campos ou tipos inválidos."},
              503:{"content":{"application/problem+json":{"schema":ApiProblem.model_json_schema()}},"description":"Armazenamento ou base de referências indisponível."}}

# Bancada isolada: consome o contrato do senior sem alterar o motor.
_test_assets = Path(__file__).parent / "static"
app.mount("/test-assets", StaticFiles(directory=_test_assets, check_dir=False), name="test-assets")


@app.get("/test", include_in_schema=False)
def test_page() -> FileResponse:
    return FileResponse(_test_assets / "test.html", headers={"Cache-Control": "no-store"})

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


def check_token(x_geosafra_token: str | None = Security(service_key)) -> None:
    if settings.api_token and x_geosafra_token != settings.api_token:
        raise HTTPException(status_code=401, detail="Token inválido.")


@app.get("/health", tags=["Sistema"], summary="Verificar serviço e versão do catálogo")
def health() -> dict:
    return {"status": "ok", "engine_version": ENGINE_VERSION, "catalog_version": load_catalog().version}


@app.get('/v1/delivery-progress', dependencies=[Depends(check_token)], response_model=DeliveryProgress,
         tags=['Sistema'], summary='Consultar matriz interna de evolucao da entrega',
         description='Percentual de criterios de aceite em revisao manual datada; nao e avaliacao oficial NASA nem validacao cientifica.')
def delivery_progress():
    return progress()


@app.get('/v1/data-readiness', dependencies=[Depends(check_token)], tags=['Fontes'],
         summary='Verificar dependências e rastreabilidade das fontes',
         description='Não consulta fontes externas. Dependência instalada não comprova disponibilidade da API.')
def data_readiness() -> dict:
    import importlib.util
    dependencies = {name: importlib.util.find_spec(name) is not None for name in ('h5py', 'rasterio')}
    return {'require_verified_profiles': settings.require_verified_profiles,
            'dependencies': dependencies,
            'earthdata_credentials_configured': bool(settings.earthdata_token),
            'external_connectivity_verified': False,
            'limitations': ['Recebimento registrado não equivale a assinatura NASA.',
                            'Catálogo agronômico ainda contém hipóteses não validadas.']}


@app.get("/v1/catalog", dependencies=[Depends(check_token)], tags=["Fontes"], summary="Consultar culturas, equipamentos e modelos de rotação")
def catalog() -> dict:
    data = load_catalog().public()
    data['evidence'] = [crop_evidence(crop) for crop in load_catalog().crops.values()]
    return data


@app.get('/v1/catalog/evidence', dependencies=[Depends(check_token)], tags=['Fontes'],
         summary='Consultar referencias e pendencias dos parametros agronomicos',
         description='Conferencia bibliografica por parametro. Nao comprova validacao regional ou acuracia das recomendacoes.')
def catalog_evidence() -> dict:
    return {'catalog_version': load_catalog().version,
            'crops': [crop_evidence(crop) for crop in load_catalog().crops.values()]}


@app.post("/v1/climate-profile", dependencies=[Depends(check_token)], tags=["Fontes"],
          summary="Consultar NASA POWER e calcular perfil climático", description="Retorna o JSON completo usado em climate no POST /v1/analysis. Inclui _receipt para comprovar integridade/local na analise. Pode demorar em consultas sem cache. Não é previsão futura.")
async def climate_profile(req: ClimateRequest) -> dict:
    t0 = time.perf_counter()
    series = await PowerClient().fetch(req.latitude, req.longitude, req.start_year, req.end_year)
    profile = build_climate_profile(series)
    profile["source"]["processing_seconds"] = round(time.perf_counter() - t0, 1)
    profile["engine_version"] = ENGINE_VERSION
    return register(profile, "climate", req.latitude, req.longitude, settings)


@app.post("/v1/terrain", dependencies=[Depends(check_token)], tags=["Fontes"], summary="Estimar relevo com SRTM", description="Resultado opcional enviado como terrain na análise. LS aproximado, sem cálculo completo de perda de solo.")
async def terrain(req: TerrainRequest) -> dict:
    profile = await TerrainClient().fetch(req.latitude, req.longitude, req.boundary)
    return register(profile, "terrain", req.latitude, req.longitude, settings)


@app.post("/v1/vegetation", dependencies=[Depends(check_token)], tags=["Fontes"], summary="Consultar cobertura verde MODIS e HLS", description="Resultado opcional enviado como vegetation na análise. Os períodos seguem a configuração do servidor.")
async def vegetation(req: VegetationRequest) -> dict:
    t0 = time.perf_counter()
    out = await NdviClient().fetch(req.latitude, req.longitude)
    out["processing_seconds"] = round(time.perf_counter() - t0, 1)
    return register(out, "vegetation", req.latitude, req.longitude, settings)


@app.post("/v1/stress", dependencies=[Depends(check_token)], tags=["Fontes"], summary="Consultar LST e ET/PET MODIS", description="Resultado opcional enviado como stress na análise. Não confundir temperatura superficial com temperatura do ar.")
async def stress(req: VegetationRequest) -> dict:
    t0 = time.perf_counter()
    out = await StressClient().fetch(req.latitude, req.longitude)
    out["processing_seconds"] = round(time.perf_counter() - t0, 1)
    return register(out, "stress", req.latitude, req.longitude, settings)


@app.post("/v1/earthdata", dependencies=[Depends(check_token)], tags=["Fontes"], summary="Consultar SMAP, GPM, ECOSTRESS e GRACE", description="Resultado opcional enviado como earthdata na análise. Requer EARTHDATA_TOKEN no servidor; fontes podem retornar null com notas.")
async def earthdata(req: VegetationRequest) -> dict:
    t0 = time.perf_counter()
    out = await EarthdataClient().fetch(req.latitude, req.longitude)
    out["processing_seconds"] = round(time.perf_counter() - t0, 1)
    return register(out, "earthdata", req.latitude, req.longitude, settings)


@app.post("/v1/analysis", dependencies=[Depends(check_token)], response_model=AnalysisResponse,
          tags=["Análises"], summary="Calcular rotações e criar um snapshot",
          description="Preserva a saída do motor e acrescenta analysis_id, created_at e expires_at. "
                      "Perfis exigem recibo _receipt valido da consulta feita neste servidor e no mesmo ponto. Guarde o ID para consultar o resultado e solicitar insights. Snapshots são locais, com TTL e limite de retenção.",
          responses=API_ERRORS)
def analysis(req: AnalysisRequest) -> dict:
    if not req.climate.get("monthly"):
        raise HTTPException(status_code=422, detail="ClimateProfile ausente ou inválido.")
    unknown = [h.crop for h in req.history if h.crop not in load_catalog().crops]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Culturas fora do catálogo: {', '.join(unknown)}")
    try:
        provenance = verify(req, settings)
        result = run(req)
        result["source_verification"] = provenance
        result['catalog_evidence'] = [crop_evidence(load_catalog().crop(slug)) for slug in sorted({
            crop for strategy in result['strategies'] for step in strategy['steps'] for crop in step['crops']})]
        result["warnings"] = [w for w in result["warnings"] if not w.startswith("Perfis ambientais recebidos")]
        result["warnings"].append(provenance["meaning"])
    except (ValueError, TypeError, IndexError, AttributeError) as exc:
        raise HTTPException(422, "Perfil invalido ou insuficiente. Consulte novamente as fontes neste servidor, sem alterar os perfis e mantendo o mesmo local.") from exc
    inputs = {"soil": req.soil.model_dump(mode="json") if req.soil else {"source":"unknown","ph_water":None},
              "crops": sorted({crop for strategy in result["strategies"] for step in strategy["steps"] for crop in step["crops"]})}
    return SnapshotStore(settings.cache_dir, settings.insights_snapshot_ttl_hours).create(result, inputs)


@app.post('/v1/cultivation-assessment', dependencies=[Depends(check_token)],
          response_model=CultivationResponse, tags=['Análises'],
          summary='Avaliar condições históricas para um cultivo', responses=API_ERRORS,
          description='Exige recibo _receipt valido de consulta no mesmo servidor e ponto. Recebe perfil climático, talhão, cultura e datas. Retorna parecer por água, clima e pH, '
                      'com evidências, regras exploratórias e lacunas. Datas aproximadas por meses; não é previsão, '
                      'ZARC, produtividade ou lucro. Exige três safras completas para concluir sobre água.')
def cultivation_assessment(req: CultivationRequest) -> dict:
    try:
        provenance = verify(req, settings)
        result = assess(req)
        result["source_verification"] = provenance
        return result
    except (ValueError, TypeError, IndexError, AttributeError) as exc:
        raise HTTPException(422, 'Cultura ou perfil inválido para esta avaliação.') from exc


@app.exception_handler(HTTPException)
async def http_problem(_: Request, exc: HTTPException) -> JSONResponse:
    return problem(exc.status_code, "Falha na requisição", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_problem(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse({"type":"about:blank","title":"Requisição inválida","status":422,
        "detail":"Confira os campos e tipos documentados no Swagger.",
        "errors":[{"loc":list(e["loc"]),"message":e["msg"],"type":e["type"]} for e in exc.errors()]},
        status_code=422, media_type="application/problem+json")


@app.exception_handler(sqlite3.Error)
async def storage_problem(_: Request, exc: sqlite3.Error) -> JSONResponse:
    return problem(503, "Armazenamento indisponível", "Não foi possível acessar os snapshots ou a base RAG.")


@app.get("/v1/analyses/{analysis_id}", dependencies=[Depends(check_token)], response_model=AnalysisResponse,
         tags=["Análises"], summary="Recuperar uma análise pelo ID",
         description="Retorna o resultado imutável guardado no servidor. Não consulta NASA nem executa Gemini.",
         responses={**API_ERRORS,404:{"content":{"application/problem+json":{"schema":ApiProblem.model_json_schema()}},"description":"Análise inexistente, expirada ou removida por retenção."}})
def get_analysis(analysis_id: UUID) -> dict:
    snapshot = SnapshotStore(settings.cache_dir, settings.insights_snapshot_ttl_hours).get(analysis_id)
    if snapshot is None:
        raise HTTPException(404, "Análise não encontrada ou expirada. Execute /v1/analysis novamente.")
    return snapshot["result"]


@app.get("/v1/insights/capabilities", dependencies=[Depends(check_token)], response_model=InsightsCapabilities,
         tags=["Insights"], summary="Consultar disponibilidade de insights",
         description="Expõe apenas capacidades e versões; nunca chaves. Fallback determinístico funciona sem Gemini.", responses=API_ERRORS)
def insights_capabilities() -> dict:
    try:
        knowledge = Knowledge(settings.rag_knowledge_dir)
    except ValueError:
        raise HTTPException(503, "Base RAG inválida; verifique os documentos aprovados.")
    return {"enabled":settings.insights_enabled,"gemini_configured":bool(settings.gemini_api_key and settings.gemini_model),
            "default_mode":"deterministic","max_gemini_attempts_per_analysis":1,
            "snapshot_ttl_hours":settings.insights_snapshot_ttl_hours,"prompt_version":PROMPT_VERSION,
            "knowledge_version":knowledge.version,"approved_chunks":len(knowledge.chunks)}


@app.post("/v1/insights", dependencies=[Depends(check_token)], response_model=InsightsResponse,
          tags=["Insights"], summary="Obter insights fundamentados de uma análise",
          description="Recebe somente analysis_id e use_gemini. Carrega o snapshot do servidor; não aceita fatos ou citações do navegador. "
                      "use_gemini=false usa templates. Gemini exige INSIGHTS_ENABLED, GEMINI_API_KEY e GEMINI_MODEL; pode consumir cota. "
                      "Há uma tentativa Gemini por snapshot. Erro, timeout ou resposta rejeitada retorna fallback HTTP 200 identificado. "
                      "checked indica checagem de formato e referências, não validação agronômica. O ranking não é alterado.",
          responses={**API_ERRORS,404:{"content":{"application/problem+json":{"schema":ApiProblem.model_json_schema()}},"description":"Snapshot inexistente ou expirado."}})
async def post_insights(req: InsightsRequest) -> dict:
    store = SnapshotStore(settings.cache_dir, settings.insights_snapshot_ttl_hours)
    snapshot = store.get(req.analysis_id)
    if snapshot is None:
        raise HTTPException(404, "Análise não encontrada ou expirada. Execute /v1/analysis novamente.")
    try:
        return await insights_for(snapshot, req.use_gemini, settings, store)
    except ValueError:
        raise HTTPException(503, "Base de referências ou contexto inválido; consulte o responsável pelo serviço.")
