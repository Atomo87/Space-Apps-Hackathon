"""Parecer historico explicavel. Limiares exploratorios, nao prognostico agronomico."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.catalog.loader import load_catalog
from app.catalog.evidence import crop_evidence
from app.engine.criteria import Ctx, step_water
from app.engine.rotation import Step
from app.engine.scenario import apply_scenario
from app.schemas import AnalysisRequest
from app.engine.temporal import TemporalComparison, compare_seasons


class CultivationRequest(AnalysisRequest):
    crop: str = Field(description="Slug de /v1/catalog.")
    sowing_date: date
    harvest_date: date
    anomaly_tolerance_pct: float = Field(default=20, ge=0, le=100,
        description='Tolerancia percentual minima para acumulado de chuva. Tambem se aplicam piso de 30 mm e faixa robusta MAD.')

    @model_validator(mode='after')
    def check_cycle(self):
        days = (self.harvest_date - self.sowing_date).days
        if days < 1 or days > 330:
            raise ValueError('Informe um ciclo entre um e 330 dias; culturas perenes exigem outro modelo.')
        return self


class AssessmentFactor(BaseModel):
    criterion: str
    status: Literal['compativel', 'atencao', 'limitante', 'sem_dados']
    explanation: str
    evidence: dict
    rule: str
    source: str
    validation_status: str = 'exploratory_not_regionally_validated'
    parameter_evidence: dict = Field(default_factory=dict)


class CultivationResponse(BaseModel):
    status: Literal['favoravel_no_historico', 'parcialmente_favoravel', 'limitacoes_relevantes', 'dados_insuficientes']
    summary: str
    crop: str
    sowing_date: date
    harvest_date: date
    factors: list[AssessmentFactor]
    limitations: list[str]
    rules_version: str
    source_verification: dict = Field(default_factory=dict)
    catalog_evidence: dict = Field(default_factory=dict)
    temporal_comparison: TemporalComparison


def assess(req: CultivationRequest) -> dict:
    catalog = load_catalog()
    if req.crop not in catalog.crops:
        raise ValueError('Cultura fora do catalogo.')
    crop = catalog.crop(req.crop)
    profile = apply_scenario(req.climate, req.scenario.rain_delta_pct, req.scenario.temp_delta_c)
    ctx = Ctx(profile, catalog, req.field, req.soil, req.constraints, None)
    step = Step([req.crop], req.sowing_date.month, req.harvest_date.month, 'cash')
    water = step_water(ctx, step)
    factors = []
    bibliography = crop_evidence(crop)
    def add(criterion, status, explanation, evidence, rule, source):
        parameters = {'agua': ['kc'], 'clima': ['t_base_c', 't_heat_stress_c', 'frost_tolerance'], 'solo': ['ph_range']}[criterion]
        factors.append(dict(criterion=criterion, status=status, explanation=explanation,
                            evidence=evidence, rule=rule, source=source,
                            validation_status='exploratory_not_regionally_validated',
                            parameter_evidence={key: bibliography['parameters'][key] for key in parameters}))
    complete = len(water['per_year'])
    deficit = water['deficit_p50']
    water_status = ('sem_dados' if complete < 3 else 'limitante' if deficit > .3 else
                    'atencao' if deficit > .1 else 'compativel')
    add('agua', water_status, 'Balanco hidrico mensal de safras historicas completas, com irrigacao informada e armazenamento presumido.',
        water, 'Minimo tres safras completas; deficit mediano ate 10% compativel, acima de 30% limitante, intervalo intermediario atencao. Limiares exploratorios.',
        'NASA POWER declarada pelo cliente + Kc do catalogo')
    temperatures = [ctx.monthly[m].get('tmean_c') for m in step.months]
    frost = max(ctx.monthly[m]['frost_prob'].get('2.0', 0) or 0 for m in step.months)
    heat = [ctx.monthly[m]['heat_days'] for m in step.months]
    from app.engine.criteria import interp_threshold
    hot_days = max(interp_threshold(h, crop['t_heat_stress_c']) for h in heat)
    thermal = ('sem_dados' if any(t is None for t in temperatures) else
               'limitante' if min(temperatures) < crop['t_base_c'] else
               'atencao' if frost >= .1 or hot_days >= 3 else 'compativel')
    add('clima', thermal, 'Temperatura media, ocorrencia historica de frio e dias quentes na janela mensal.',
        {'monthly_tmean_c': temperatures, 't_base_c': crop['t_base_c'], 'frost_frequency': frost,
         'heat_days_max': hot_days, 'heat_threshold_c': crop['t_heat_stress_c'], 'months': step.months},
        'Media abaixo da base: limitante. Frio <=2 C em pelo menos 10% dos anos ou pelo menos tres dias quentes/mes: atencao; demais casos compativeis neste rastreio.',
        'NASA POWER declarada pelo cliente + catalogo simplificado')
    ph = req.soil.ph_water if req.soil else None
    lo, hi = crop['ph_range']
    soil_status = 'sem_dados' if ph is None else 'compativel' if lo <= ph <= hi else 'limitante'
    add('solo', soil_status, 'Compatibilidade restrita ao pH informado; nao e avaliacao completa do solo.',
        {'ph_water': ph, 'catalog_range': [lo, hi], 'origin': req.soil.source if req.soil else 'unknown',
         'sampled_at': req.soil.sampled_at.isoformat() if req.soil and req.soil.sampled_at else None,
         'analysis_provider': req.soil.analysis_provider if req.soil else None,
         'report_reference': req.soil.report_reference if req.soil else None,
         'origin_verified': False},
        'pH ausente: sem dados; dentro da faixa do catalogo: compativel; fora: limitante, sem prescrever correcao.',
        'Produtor + catalogo simplificado')
    statuses = [f['status'] for f in factors]
    status = ('limitacoes_relevantes' if 'limitante' in statuses else
              'dados_insuficientes' if water_status == 'sem_dados' or thermal == 'sem_dados' else
              'parcialmente_favoravel' if 'sem_dados' in statuses or 'atencao' in statuses else 'favoravel_no_historico')
    summaries = {'limitacoes_relevantes': 'Ha limitacoes relevantes no rastreio historico.',
                 'dados_insuficientes': 'Faltam evidencias para concluir sobre as condicoes do cultivo.',
                 'parcialmente_favoravel': 'Condicoes historicas parcialmente favoraveis, com ressalvas ou lacunas.',
                 'favoravel_no_historico': 'Condicoes compativeis nos criterios historicos avaliados.'}
    return dict(status=status, summary=summaries[status], crop=req.crop, sowing_date=req.sowing_date,
        harvest_date=req.harvest_date, factors=factors, rules_version='cultivation-screening-v1', catalog_evidence=crop_evidence(crop),
        temporal_comparison=compare_seasons(profile, step.months, req.sowing_date.year, req.anomaly_tolerance_pct), limitations=[
            'Historico e cenario exploratorio, nao previsao do ano de plantio, produtividade ou lucro.',
            'Datas sao aproximadas por meses; nao avalia fases fenologicas nem veranicos diarios.',
            'Nao substitui ZARC, analise completa de solo ou revisao agronomica. Catalogo e limiares sao hipoteses a validar.',
            'Resolucao regional POWER; origem dos perfis declarada pelo cliente. Irrigacao nao comprova outorga ou disponibilidade.',
            'Irrigacao, textura, armazenamento e Kc podem introduzir erro no balanco mensal.'])
