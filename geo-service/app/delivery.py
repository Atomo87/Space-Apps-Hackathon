"""Indicador interno de aceite do MVP, nao nota NASA nem acuracia cientifica.

Cada criterio vale uma unidade dentro de seu eixo. A revisao e manual e datada;
existencia de codigo nao marca automaticamente uma consulta real como concluida.
"""
from pydantic import BaseModel


class Criterion(BaseModel):
    description: str
    complete: bool
    evidence: str


class Objective(BaseModel):
    key: str
    title: str
    weight: int
    percent: float
    criteria: list[Criterion]


class DeliveryProgress(BaseModel):
    rubric_version: str
    reviewed_on: str
    overall_percent: float
    ready_for_delivery: bool
    objectives: list[Objective]
    interpretation: str
    next_steps: list[str]


# Matriz de criterios de aceite definida pelo projeto. Nao e rubrica oficial.
RUBRIC = [
    ('nasa', 'Observacoes NASA', 20, [
        ('Clientes de consulta implementados', True, 'app/power/client.py e clientes complementares'),
        ('Indicadores e qualidade calculados', True, 'app/climate/indicators.py'),
        ('Integridade/local dos perfis registrados', True, 'app/provenance.py; tests/test_provenance.py'),
        ('Dependencias completas instaladas e verificadas', False, 'h5py/rasterio ausentes na ultima verificacao; instalacao local falhou'),
        ('Consulta real homologada pelo servidor acessivel', False, 'docs/homologacao-http.json: blocked na ultima execucao'),
        ('Caso NASA real reproduzivel apresentado', False, 'Sem homologacao documentada')]),
    ('soil', 'Solo local', 10, [
        ('Entrada de solo local', True, 'app/schemas.py: SoilInfo'),
        ('Uso de pH/textura com lacunas explicitas', True, 'app/engine/cultivation.py e criteria.py'),
        ('Data e referencia de origem estruturadas', True, 'SoilInfo: sampled_at, analysis_provider e report_reference; origem declarada, nao autenticada'),
        ('Caso de campo com solo comprovavel', False, 'Nao fornecido nem homologado')]),
    ('crops', 'Caracteristicas das culturas', 20, [
        ('Catalogo estruturado usado pelo motor', True, 'app/catalog/loader.py'),
        ('Conferencia inicial de Kc rastreavel', True, 'app/catalog/evidence.py; FAO-56 para quatro culturas'),
        ('Demais parametros essenciais com referencias especificas', False, 'pH, temperatura, pragas e atributos de solo ainda pendentes'),
        ('Revisao regional por responsavel tecnico', False, 'Nao realizada')]),
    ('priorities', 'Prioridades do produtor', 10, [
        ('Pesos ajustaveis', True, 'app/schemas.py: Priorities'),
        ('Restricoes de equipamento/cultura/mercado', True, 'app/engine/criteria.py'),
        ('Efeito do ranking coberto em teste', True, 'tests/test_engine.py'),
        ('Validacao com produtor em caso real', False, 'Nao realizada')]),
    ('rotation', 'Explorar rotacoes', 20, [
        ('Referencia da rotacao atual', True, 'app/engine/rotation.py'),
        ('Alternativas com pontuacao e diversidade', True, 'app/engine/engine.py'),
        ('Explicacoes, evidencias e lacunas', True, 'app/engine/engine.py: explain'),
        ('Filtros e janelas agronomicas regionais homologados', False, 'Hipoteses exploratorias; nao equivale a ZARC'),
        ('Comparacao validada num caso real', False, 'Nao homologada')]),
    ('resilience', 'Solo e resiliencia', 10, [
        ('Indicadores exploratorios de agua e cobertura', True, 'app/engine/criteria.py'),
        ('Cenarios e comparacao temporal', True, 'app/engine/scenario.py e temporal.py'),
        ('Resultados conferidos com observacoes de campo', False, 'Nao realizados'),
        ('Beneficios propostos revisados tecnicamente', False, 'Nao homologados')]),
    ('delivery', 'Entrega HTTP e interface', 10, [
        ('Tela e parecer implementados', True, 'app/static/test.html e test.js'),
        ('Contratos HTTP e Swagger', True, 'app/main.py; testes ASGI'),
        ('Testes automatizados executados', True, '101 testes Python aprovados na revisao anterior; suite JS aprovada'),
        ('Servidor e interface homologados no navegador', False, '404/portas reportados; inspecao visual nao concluida'),
        ('Fluxo real completo homologado', False, 'verify-delivery.py ainda sem resultado aprovado')]),
]


def progress():
    objectives = []
    for key, title, weight, criteria in RUBRIC:
        percentage = 100 * sum(complete for _, complete, _ in criteria) / len(criteria)
        objectives.append(Objective(key=key, title=title, weight=weight, percent=round(percentage, 1),
            criteria=[Criterion(description=d, complete=c, evidence=e) for d, c, e in criteria]))
    overall = sum(o.weight * o.percent for o in objectives) / sum(o.weight for o in objectives)
    return DeliveryProgress(rubric_version='mvp-acceptance-v1', reviewed_on='2026-11-15',
        overall_percent=round(overall, 1), ready_for_delivery=False, objectives=objectives,
        interpretation='Estimativa interna de conclusao dos criterios de aceite do MVP. Nao e porcentagem oficial do desafio, acuracia, cobertura cientifica ou probabilidade de sucesso. Revisao manual datada, nao monitoramento em tempo real. Primeira linha de base numerica; nao ha percentual anterior comparavel.',
        next_steps=['Instalar dependencias e homologar consulta NASA real.',
                    'Registrar origem/data dos dados locais de solo e validar um caso de campo.',
                    'Revisar parametros agronomicos e demonstrar rotacoes no mesmo caso.',
                    'Homologar servidor, interface e fluxo completo no computador da apresentacao.'])
