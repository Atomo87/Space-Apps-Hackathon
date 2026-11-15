"""Comparacoes robustas entre janelas mensais equivalentes, sem previsao.

Cada safra e comparada com as demais: o proprio valor nao dilui sua anomalia.
MAD e tolerancia sao regras exploratorias, nao teste de significancia climatica.
"""
import math
from statistics import median
from typing import Literal

from pydantic import BaseModel


class SeasonComparison(BaseModel):
    sowing_year: int
    harvest_year: int
    rain_mm: float | None
    eto_mm: float | None
    reference_median_mm: float | None
    rain_difference_pct: float | None
    tolerance_mm: float | None
    classification: Literal['dentro_da_faixa', 'mais_seca', 'mais_chuvosa', 'sem_dados', 'referencia_insuficiente']
    reference_count: int
    missing_months: list[str]


class TemporalComparison(BaseModel):
    method: str
    tolerance_pct: float
    min_reference_seasons: int
    seasons: list[SeasonComparison]
    requested_sowing_year: int
    requested_year_available: bool
    notes: list[str]


def compare_seasons(profile, months, requested_year, tolerance_pct=20):
    monthly = {m['month']: m for m in profile['monthly']}
    years = sorted({int(y) for y in profile['yearly']['years']})
    rows = []
    for year in years:
        rain = eto = 0.
        missing = []
        for month in months:
            calendar_year = year + (month < months[0])
            data = monthly[month]
            r = data['rain_by_year'].get(str(calendar_year))
            e = data['eto_by_year'].get(str(calendar_year))
            if any(v is None or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (r, e)):
                missing.append(f'{calendar_year}-{month:02}')
            else:
                rain += r
                eto += e
        rows.append(dict(sowing_year=year, harvest_year=year + (months[-1] < months[0]),
            rain_mm=round(rain, 2) if not missing else None,
            eto_mm=round(eto, 2) if not missing else None,
            reference_median_mm=None, rain_difference_pct=None, tolerance_mm=None,
            classification='sem_dados' if missing else 'referencia_insuficiente',
            reference_count=0, missing_months=missing))
    for row in rows:
        if row['rain_mm'] is None:
            continue
        reference = [r['rain_mm'] for r in rows if r is not row and r['rain_mm'] is not None]
        row['reference_count'] = len(reference)
        if len(reference) < 5:
            continue
        center = median(reference)
        mad = median(abs(v - center) for v in reference)
        # Piso absoluto evita exagerar diferencas em janelas quase sem chuva.
        tolerance = max(30., center * tolerance_pct / 100, 3 * 1.4826 * mad)
        delta = row['rain_mm'] - center
        row.update(reference_median_mm=round(center, 2), tolerance_mm=round(tolerance, 2),
                   rain_difference_pct=round(100 * delta / center, 1) if center > 0 else None,
                   classification='mais_seca' if delta < -tolerance else
                   'mais_chuvosa' if delta > tolerance else 'dentro_da_faixa')
    return dict(method='mediana_das_demais_safras_com_MAD', tolerance_pct=tolerance_pct,
        min_reference_seasons=5, seasons=rows, requested_sowing_year=requested_year,
        requested_year_available=any(r['sowing_year'] == requested_year and r['rain_mm'] is not None for r in rows),
        notes=['Chuva e ETo somam meses inteiros da mesma janela; nao sao o balanco hidrico parcial do cultivo.',
               'Cada safra e comparada com pelo menos cinco outras safras completas, excluindo a si propria.',
               'Faixa: maior entre tolerancia percentual, 30 mm e tres vezes 1,4826 MAD; igualdade fica dentro da faixa.',
               'Ano ausente ou janela incompleta nao e classificado nem previsto. Zero de referencia nao gera percentual.',
               'Atipicidade refere-se somente ao acumulado de chuva, nao a distribuicao diaria, temperatura ou produtividade.',
               'Serie curta nao constitui normal climatologica; MAD nao e probabilidade nem teste de significancia.',
               'Cenarios alteram toda a serie: comparacoes descrevem o cenario selecionado.'])
