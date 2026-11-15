"""Conferencia bibliografica por parametro; nao equivale a validacao regional."""
FAO_URL = 'https://www.fao.org/4/x0490e/x0490e0b.htm'
REVIEWED = {
    'soja': {'values': {'ini': .4, 'mid': 1.15, 'end': .5}, 'row': 'Soybeans; ini herdado do grupo Legumes', 'status': 'matches_reference'},
    'milho': {'values': {'ini': .3, 'mid': 1.2, 'end': .6}, 'row': 'Maize, Field (grain); Kc end 0.60–0.35, conforme colheita', 'status': 'selected_from_reference_range'},
    'milheto': {'values': {'ini': .3, 'mid': 1., 'end': .3}, 'row': 'Millet; ini herdado do grupo Cereals', 'status': 'matches_reference'},
    'sorgo': {'values': {'ini': .3, 'mid': 1.05, 'end': .55}, 'row': 'Sorghum grain; Kc mid 1.00–1.10; 1.05 e ponto medio adotado', 'status': 'selected_from_reference_range'},
}

CONTEXT = {
    'soja': {
        'ph_range': {'values': [5.5, 7.8], 'section': '3.5 Habitat',
            'note': 'Tolerancia geral publicada, nao faixa otima nem recomendacao para pH em agua no Cerrado.'},
        't_base_c': {'values': 10, 'section': '3.5 Habitat',
            'note': 'Minimo citado para temperatura do solo na germinacao; nao valida comparacao com temperatura media mensal do ar.'},
        't_heat_stress_c': {'values': [10, 40], 'section': '3.5 Habitat',
            'note': 'Intervalo de temperatura de cultivo; nao determina limiar unico de estresse. Limiar 35 do catalogo nao foi validado por esta fonte.'},
    },
    'milho': {
        'ph_range': {'values': {'optimal': [5, 7], 'absolute': [4.5, 8.5]}, 'section': 'Ecology: Soil PH',
            'note': 'Optimo e tolerancia absoluta sao conceitos distintos; metodo de medicao de pH nao especificado. Nao valida automaticamente faixa local 5.5–7.'},
        't_base_c': {'values': {'optimal': [18, 33], 'absolute': [10, 47]}, 'section': 'Ecology: Temperature requirements',
            'note': 'Limites ecologicos gerais nao equivalem a temperatura-base fenologica nem a risco em uma media mensal.'},
    },
}


def contextual_reference(slug):
    return ({'title': 'CFIA BIO2021-01: The Biology of Glycine max',
             'url': 'https://inspection.canada.ca/en/plant-varieties/plants-novel-traits/applicants/directive-94-08/biology-documents/glycine-max-merr'}
            if slug == 'soja' else {'title': 'FAO EcoCrop: Zea mays',
             'url': 'https://ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=2175'})


def crop_evidence(crop):
    result = {}
    for parameter, value in crop.raw.items():
        if parameter in {'sources', 'hypotheses', 'local_review_risks'}:
            continue
        result[parameter] = {'status': 'not_verified_in_this_review', 'regional_validation': 'pending'}
    entry = REVIEWED.get(crop.slug)
    if entry and crop['kc'] == entry['values']:
        result['kc'] = {'status': entry['status'], 'regional_validation': 'pending',
                        'reference': {'title': 'FAO Irrigation and Drainage Paper 56', 'url': FAO_URL,
                                      'section': 'Chapter 6, Table 12', 'row': entry['row'], 'checked_on': '2026-11-15'},
                        'limitations': ['Condicoes padrao da referencia; exige ajustes por clima, molhamento e fases.',
                                        'Conferencia bibliografica nao valida o balanco mensal simplificado do GeoSafra.']}
    for parameter, context in CONTEXT.get(crop.slug, {}).items():
        result[parameter] = {
            'status': 'context_only_not_parameter_validation', 'regional_validation': 'pending',
            'catalog_value': crop[parameter], 'published_context': context['values'],
            'reference': {**contextual_reference(crop.slug), 'section': context['section'], 'checked_on': '2026-11-15'},
            'limitations': [context['note'], 'Nao substituir parametros automaticamente; requer revisao tecnica local.']}
    return {'crop': crop.slug, 'parameters': result,
            'overall_status': 'not_regionally_validated',
            'note': 'Fonte generica citada no catalogo nao significa parametro conferido. Campos sem referencia especifica permanecem pendentes.'}
