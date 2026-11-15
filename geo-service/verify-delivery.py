"""Homologacao HTTP real. Nao inicia servidor e nao usa mocks.

Execute com o servidor aberto: python verify-delivery.py --port 8010 --live-power
Credenciais sao carregadas da configuracao local e nunca entram no relatorio.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

import httpx

from app.config import settings


def verify(port, live_power=False):
    checks = []
    headers = {'X-GeoSafra-Token': settings.api_token} if settings.api_token else {}
    def record(name, passed, detail):
        checks.append({'check': name, 'passed': passed, 'detail': detail})
    with httpx.Client(base_url=f'http://127.0.0.1:{port}', headers=headers,
                      timeout=180, trust_env=False) as client:
        def get(path):
            response = client.get(path)
            response.raise_for_status()
            return response
        try:
            health = get('/health').json()
            record('health', health.get('status') == 'ok', 'Servico responde em HTTP.')
            schema = get('/openapi.json').json()
            paths = schema.get('paths', {})
            required = ['/v1/cultivation-assessment', '/v1/insights', '/v1/analyses/{analysis_id}']
            missing = [p for p in required if p not in paths]
            record('version_routes', not missing, 'Rotas da versao esperada presentes.' if not missing else 'Servidor incorreto ou antigo; faltam: '+', '.join(missing))
            page = get('/test').text
            record('test_page', all(marker in page for marker in ['planned-crop', 'anomaly-tolerance', 'assess-cultivation']),
                   'Conferidos controles de cultivo e comparacao temporal.')
            for asset in ['test.js', 'test.css']:
                response = get('/test-assets/'+asset)
                record(asset, bool(response.content), 'Asset acessivel.')
            record('swagger', 'swagger-ui' in get('/docs').text.lower(), 'Pagina Swagger acessivel.')
            catalog = get('/v1/catalog').json()
            record('catalog', any(c.get('slug') == 'soja' for c in catalog.get('crops', [])), 'Catalogo consultado com autenticacao local, quando configurada.')
            if live_power and all(c['passed'] for c in checks):
                climate_response = client.post('/v1/climate-profile', json={
                    'latitude': -18.9186, 'longitude': -48.2772,
                    'start_year': 2015, 'end_year': 2025})
                climate_response.raise_for_status()
                climate = climate_response.json()
                record('power_real', len(climate.get('monthly', [])) == 12,
                       'Consulta real ao endpoint POWER concluida; pode usar cache real do servidor. Local de exemplo, nao propriedade do usuario.')
                body = {'climate': climate, 'field': {'latitude': -18.9186, 'longitude': -48.2772}}
                assessment = client.post('/v1/cultivation-assessment', json={**body,
                    'crop': 'soja', 'sowing_date': '2026-10-20', 'harvest_date': '2027-02-15'})
                assessment.raise_for_status()
                result = assessment.json()
                soil = next((f for f in result.get('factors', []) if f['criterion'] == 'solo'), {})
                record('cultivation_real', soil.get('status') == 'sem_dados' and bool(result.get('temporal_comparison')),
                       'Parecer calculado sobre perfil real; ausencia de pH preservada.')
                analysis = client.post('/v1/analysis', json=body)
                analysis.raise_for_status()
                identifier = analysis.json()['analysis_id']
                saved = get('/v1/analyses/'+identifier).json()
                record('snapshot', saved.get('analysis_id') == identifier, 'Analise criada e recuperada.')
                insight = client.post('/v1/insights', json={'analysis_id': identifier, 'use_gemini': False})
                insight.raise_for_status()
                record('fallback', insight.json().get('generation_mode') == 'deterministic', 'Explicacao deterministica acessivel; Gemini nao chamado.')
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            # Nunca copiar corpo externo, URL de erro, cabecalhos ou tokens.
            code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
            record('execution', False, f'Falha {type(exc).__name__}' + (f' HTTP {code}.' if code else '. Verifique servidor, porta e conectividade.'))
    passed = bool(checks) and all(c['passed'] for c in checks)
    return {'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'port': port,
            'live_power_requested': live_power,
            'status': 'http_flow_passed' if passed and live_power else 'http_smoke_passed' if passed else 'blocked',
            'checks': checks,
            'limitations': ['Nao valida visualmente o navegador, acuracia agronomica, fontes opcionais ou Gemini.',
                            'Modo live-power cria um snapshot temporario de teste, sem identificacao de produtor.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8010)
    parser.add_argument('--live-power', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Porta deve estar entre 1 e 65535.')
    report = verify(args.port, args.live_power)
    destination = Path(__file__).resolve().parent / 'docs/homologacao-http.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    for check in report['checks']:
        print(('OK' if check['passed'] else 'FALHOU') + ' - ' + check['check'] + ': ' + check['detail'])
    print('Resultado: ' + report['status'])
    print('Relatorio: ' + str(destination))
    return 1 if report['status'] == 'blocked' else 0


if __name__ == '__main__':
    sys.exit(main())
