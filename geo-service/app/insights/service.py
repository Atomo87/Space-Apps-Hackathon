"""Geracao opcional com evidencias resolvidas no servidor e fallback deterministico."""
import hashlib
import json
import math
import re
from pathlib import Path

import httpx

from app.insights.contracts import Fact, GeneratedInsights, Insight
from app.insights.knowledge import Knowledge

PROMPT_VERSION = "geosafra-insights-v2"
PROMPT = Path(__file__).resolve().parents[2] / "docs" / "rag" / "system-prompt.txt"


def build_facts(snapshot):
    result, inputs = snapshot["result"], snapshot["inputs"]
    facts = []
    period = (result.get("diagnosis", {}).get("source", {}).get("period") or {})
    period_label = str(period.get("start", "?")) + " a " + str(period.get("end", "?"))
    def add(identifier, label, path, value, unit, source, limitations=(), fact_period=None):
        if isinstance(value, float) and not math.isfinite(value):
            value = None
        facts.append(Fact(id=identifier, label=label, path=path, value=value, unit=unit,
                          source=source, period=fact_period or ((inputs.get("soil") or {}).get("sampled_at") or "Data de coleta nao informada" if source == "Produtor" else "2000" if source == "SRTM" else period_label), limitations=list(limitations)))
    soil = inputs.get("soil") or {}
    add("soil-ph", "pH em agua informado", "/inputs/soil/ph_water", soil.get("ph_water"), None,
        "Produtor", ["Origem: " + soil.get("source", "unknown"), "Ausencia de dado nao significa solo adequado."])
    diagnosis = result.get("diagnosis", {})
    for index, month in enumerate(diagnosis.get("monthly", [])):
        if len(facts) >= 18:
            break
        add("rain-"+str(month["month"]), "Chuva media: "+month["name"],
            f"/result/diagnosis/monthly/{index}/rain_mm/mean", month.get("rain_mm", {}).get("mean"), "mm", "NASA POWER",
            ["Dado regional historico; acumulado mensal nao descreve distribuicao diaria."])
    for index, strategy in enumerate(result.get("strategies", [])):
        add("score-"+str(index), strategy["title"], f"/result/strategies/{index}/score", strategy.get("score"), "pontos", "Motor GeoSafra",
            ["Indice heuristico; nao e probabilidade de sucesso, produtividade ou lucro."])
    terrain = diagnosis.get("terrain")
    if terrain:
        add("terrain-slope", "Declividade media estimada", "/result/diagnosis/terrain/slope_pct/mean",
            terrain.get("slope_pct", {}).get("mean"), "%", "SRTM", ["Grade amostrada e rampa presumida; nao mede erosao."])
    vegetation = diagnosis.get("vegetation")
    if vegetation:
        add("vegetation-ndvi", "NDVI recente", "/result/diagnosis/vegetation/recent/ndvi", vegetation.get("recent", {}).get("ndvi"),
            None, "MODIS", ["Baixo NDVI nao comprova solo descoberto; pixel inclui vizinhanca."], fact_period=str(vegetation.get("recent", {}).get("date") or vegetation.get("recent", {}).get("datetime") or "Data da observacao nao informada"))
    # Normalizadores explicitos: preservar unidade, escala e periodo de cada produto.
    products = [
        ("stress", "lst", "hottest/p50", "Temperatura superficial no mes mais quente", "C", "MODIS LST"),
        ("stress", "et", "ratio", "Razao ET/PET historica", None, "MODIS ET"),
        ("earthdata", "smap", "recent/sm", "Umidade superficial recente", "m3/m3", "SMAP"),
        ("earthdata", "gpm", "annual_mm", "Chuva anual media", "mm/ano", "GPM"),
        ("earthdata", "ecostress", "median_esi", "Indice evaporativo mediano", None, "ECOSTRESS"),
        ("earthdata", "grace", "latest/cm", "Anomalia regional de armazenamento de agua", "cm", "GRACE-FO"),
    ]
    for group, key, metric, label, unit, source in products:
        product = (diagnosis.get(group) or {}).get(key) or {}
        value = product
        for part in metric.split("/"):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            continue
        coverage = product.get("coverage") or {}
        years = product.get("yearly") or []
        own_period = (str(coverage.get("start")) + " a " + str(coverage.get("end"))
                      if coverage.get("start") and coverage.get("end") else
                      str(years[0].get("year")) + " a " + str(years[-1].get("year")) if years else
                      str((product.get("latest") or {}).get("datetime") or "Periodo proprio nao informado"))
        add("sensor-" + key, label, f"/result/diagnosis/{group}/{key}/{metric}", value, unit, source,
            ["Produto complementar; escalas e periodos distintos nao demonstram causalidade nem resposta da cultura.",
             "Origem ambiental declarada pelo cliente, sem autenticacao externa."], fact_period=own_period)
    return facts


def deterministic(facts):
    insights = []
    soil = next(f for f in facts if f.id == "soil-ph")
    if soil.value is None:
        insights.append(Insight(kind="observation", title="Informacao de solo pendente",
            explanation="O pH nao foi informado. Essa lacuna deve permanecer visivel na avaliacao.",
            fact_ids=[soil.id], reference_ids=[], limitations=["Nao permite concluir a compatibilidade do pH com a cultura."],
            questions_for_farmer=["Voce possui analise de solo com pH em agua e data da coleta?"]))
    scores = [f.id for f in facts if f.id.startswith("score-") and f.value is not None]
    if scores:
        insights.append(Insight(kind="observation", title="Comparacao conforme os criterios do motor",
            explanation="As pontuacoes comparam as estrategias calculadas. Nao representam chance de boa colheita ou ganho financeiro.",
            fact_ids=scores[:4], reference_ids=[], limitations=["Regras e catalogo simplificados exigem revisao local."], questions_for_farmer=[]))
    rain = next((f for f in facts if f.id.startswith("rain-") and f.value is not None), None)
    sensors = [f for f in facts if f.id.startswith("sensor-")]
    if sensors:
        insights.append(Insight(kind="observation", title="Observacoes ambientais complementares",
            explanation="Os sensores acrescentam observacoes ambientais. As escalas e os periodos devem ser conferidos antes de relacionar os valores ao cultivo.",
            fact_ids=[f.id for f in sensors], reference_ids=[], limitations=["Nao demonstram causalidade, sucesso da cultura ou disponibilidade de agua para irrigacao."], questions_for_farmer=[]))
    if rain and len(insights) < 3:
        insights.append(Insight(kind="observation", title="Chuva historica como contexto",
            explanation="O acumulado mensal descreve o historico regional. Sozinho, nao comprova agua suficiente durante o ciclo.",
            fact_ids=[f.id for f in facts if f.id.startswith("rain-") and f.value is not None], reference_ids=[], limitations=rain.limitations, questions_for_farmer=[]))
    return insights[:3]


def validate_generated(output, facts, references):
    result = GeneratedInsights.model_validate(output)
    fact_ids, reference_ids = {f.id for f in facts}, {r.id for r in references}
    for insight in result.insights:
        if not set(insight.fact_ids) <= fact_ids or not set(insight.reference_ids) <= reference_ids:
            raise ValueError("Referencia inexistente.")
        if insight.kind != "observation" and not insight.reference_ids:
            raise ValueError("Interpretacao sem referencia agronomica.")
        text = " ".join([insight.title, insight.explanation, *insight.limitations, *insight.questions_for_farmer])
        if re.search(r"\d|https?://", text):
            raise ValueError("Numeros e URLs devem vir das evidencias resolvidas.")
        if re.search(r"garantid[oa]|sera prospera|lucro certo", text, re.I):
            raise ValueError("Promessa nao sustentada.")
    # Texto livre nao pode ser provado por IDs. Aceitar apenas proposicoes
    # conservadoras cujo predicado e conferido deterministicamente.
    for insight in result.insights:
        soil = next((f for f in facts if f.id == "soil-ph"), None)
        if not (insight.kind == "observation" and insight.fact_ids == ["soil-ph"]
                and soil is not None and soil.value is None
                and insight.explanation == "O pH nao foi informado."
                and insight.title == "Solo pendente"
                and insight.limitations == ["Exige revisao local."]
                and not insight.questions_for_farmer and not insight.reference_ids):
            raise ValueError("Proposicao livre sem verificacao semantica; usar templates seguros.")
    return result.insights


async def generate_gemini(cfg, facts, references, transport=None):
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", cfg.gemini_model):
        raise ValueError("Modelo Gemini invalido.")
    context = {"facts": [f.model_dump() for f in facts], "references": [r.model_dump() for r in references]}
    # O contexto nao inclui coordenadas, tokens, nome ou identificador do produtor.
    body = {"systemInstruction": {"parts": [{"text": PROMPT.read_text(encoding="utf-8")}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(context, ensure_ascii=False)}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": GeneratedInsights.model_json_schema(),
                                 "maxOutputTokens": cfg.insights_max_output_tokens}}
    async with httpx.AsyncClient(timeout=cfg.insights_timeout_seconds, transport=transport) as client:
        response = await client.post("https://generativelanguage.googleapis.com/v1beta/models/"+cfg.gemini_model+":generateContent",
                                     headers={"x-goog-api-key": cfg.gemini_api_key}, json=body)
    if response.status_code != 200:
        # Nao repassar corpo externo: pode conter dados de conta ou configuracao.
        raise ValueError("gemini_http_"+str(response.status_code))
    data = response.json()
    candidate = data.get("candidates", [{}])[0]
    if candidate.get("finishReason") not in (None, "STOP"):
        raise ValueError("Gemini nao concluiu a resposta.")
    raw = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []) if not p.get("thought"))
    return validate_generated(json.loads(raw), facts, references)


async def insights_for(snapshot, use_gemini, cfg, store, transport=None):
    facts = build_facts(snapshot)
    # Falhas opcionais nunca tornam o fallback indisponivel.
    dependency_reason = None
    try:
        knowledge = Knowledge(cfg.rag_knowledge_dir)
    except (ValueError, OSError):
        knowledge = None
        dependency_reason = "knowledge_unavailable"
    crops = snapshot["inputs"].get("crops", [])
    references = knowledge.retrieve(" ".join(crops)+" agua solo chuva cobertura rotacao", crops) if knowledge else []
    knowledge_version = knowledge.version if knowledge else "unavailable"
    configured = cfg.insights_enabled and bool(cfg.gemini_api_key) and bool(cfg.gemini_model)
    identifier = snapshot["result"]["analysis_id"]
    try:
        prompt_hash = hashlib.sha256(PROMPT.read_bytes()).hexdigest()
    except OSError:
        prompt_hash = "unavailable"
        dependency_reason = "prompt_unavailable"
    # Cache separado por modo/configuracao, modelo e versao das referencias.
    key = hashlib.sha256(json.dumps([identifier,PROMPT_VERSION,prompt_hash,knowledge_version,use_gemini,configured,cfg.gemini_model]).encode()).hexdigest()
    cached = store.cached(key)
    if cached:
        return dict(cached, cache_hit=True)
    insights, reason, mode = deterministic(facts), "gemini_not_requested", "deterministic"
    if use_gemini:
        if dependency_reason:
            reason = dependency_reason
        elif not configured:
            reason = "gemini_not_configured_or_disabled"
        elif not store.claim_generation(identifier):
            reason = "gemini_attempt_used_in_progress_or_daily_budget"
        else:
            try:
                insights = await generate_gemini(cfg, facts, references, transport)
                mode, reason = "gemini", None
            except (httpx.HTTPError, ValueError, KeyError, IndexError, OSError):
                reason = "gemini_unavailable_or_response_rejected"
    used_facts = {fid for insight in insights for fid in insight.fact_ids}
    used_references = {rid for insight in insights for rid in insight.reference_ids}
    response = {"analysis_id": identifier, "status": "insufficient_evidence" if not insights else "checked" if mode=="gemini" else "fallback",
        "generation_mode":mode,"model":cfg.gemini_model if mode=="gemini" else None,
        "prompt_version":PROMPT_VERSION,"prompt_hash":prompt_hash,"knowledge_version":knowledge_version,"snapshot_hash":snapshot["snapshot_hash"],
        "cache_hit":False,"insights":[i.model_dump() for i in insights],
        "resolved_evidence":[f.model_dump() for f in facts if f.id in used_facts],
        "references":[r.model_dump() for r in references if r.id in used_references],
        "validation_notes":["Formato e IDs verificados; validacao semantica automatica e limitada.",
                            "Notas e ranking do motor foram preservados."],"fallback_reason":reason}
    # Nao guardar fallback de uma chamada simultanea enquanto a primeira termina.
    if reason != "gemini_attempt_used_in_progress_or_daily_budget":
        store.save(key, identifier, response)
    return response
