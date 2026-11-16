import json
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app import main
from app.climate.indicators import build_climate_profile
from app.insights import service
from app.insights.knowledge import Knowledge
from app.insights.store import SnapshotStore
from tests.synthetic import synthetic_series


@pytest.fixture
def setup(monkeypatch, tmp_path):
    cfg = replace(main.settings, cache_dir=tmp_path, rag_knowledge_dir=tmp_path / "knowledge",
                  api_token="", insights_enabled=False, gemini_api_key="", gemini_model="")
    monkeypatch.setattr(main, "settings", cfg)
    client = TestClient(main.app)
    response = client.post('/v1/analysis', json={
        "climate": build_climate_profile(synthetic_series(2020, 2023)),
        "field": {"latitude": -18.9186, "longitude": -48.2772},
        "history": [{"crop":"soja", "sown_at":"2022-10-20", "harvested_at":"2023-02-15"}]
    })
    assert response.status_code == 200, response.text
    return client, response.json(), cfg


def test_snapshot_and_fallback_chain(setup):
    client, analysis, cfg = setup
    saved = client.get('/v1/analyses/'+analysis['analysis_id'])
    assert saved.status_code == 200 and saved.json() == analysis
    response = client.post('/v1/insights', json={"analysis_id":analysis['analysis_id']})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['status'] == 'fallback' and body['generation_mode'] == 'deterministic'
    assert body['model'] is None and body['insights']
    facts = {f['id'] for f in body['resolved_evidence']}
    assert all(set(i['fact_ids']) <= facts for i in body['insights'])
    again = client.post('/v1/insights', json={"analysis_id":analysis['analysis_id']}).json()
    assert again['cache_hit'] is True
    assert again['insights'] == body['insights']


def test_not_found_expiration_and_untrusted_body(setup):
    client, analysis, cfg = setup
    assert client.post('/v1/insights', json={"analysis_id":str(uuid4())}).status_code == 404
    assert client.post('/v1/insights', json={"analysis_id":analysis['analysis_id'],"facts":[]}).status_code == 422
    assert client.get('/v1/analyses/not-a-uuid').status_code == 422
    store=SnapshotStore(cfg.cache_dir)
    with store.connect() as db:
        db.execute('UPDATE snapshots SET expires=0 WHERE id=?',(analysis['analysis_id'],))
    assert client.get('/v1/analyses/'+analysis['analysis_id']).status_code == 404


def test_capabilities_and_authentication(setup, monkeypatch):
    client, analysis, cfg = setup
    assert client.get('/v1/insights/capabilities').json()['approved_chunks'] == 0
    monkeypatch.setattr(main,'settings',replace(cfg,api_token='dummy-service-token'))
    assert client.post('/v1/insights',json={"analysis_id":analysis['analysis_id']}).status_code == 401
    assert client.get('/v1/analyses/'+analysis['analysis_id']).status_code == 401
    assert client.get('/v1/insights/capabilities',headers={'X-GeoSafra-Token':'dummy-service-token'}).status_code == 200


def install_fake_gemini(monkeypatch, cfg, output, status=200):
    monkeypatch.setattr(main,'settings',replace(cfg,insights_enabled=True,gemini_api_key='dummy-gemini-key',gemini_model='gemini-test-only'))
    calls=[]
    def handler(request):
        calls.append(request)
        assert request.headers['x-goog-api-key'] == 'dummy-gemini-key'
        assert 'dummy-gemini-key' not in request.content.decode()
        assert '-18.9186' not in request.content.decode()
        assert json.loads(request.content)['generationConfig']['responseMimeType']=='application/json'
        return httpx.Response(status,json={"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":json.dumps(output)}]}}]})
    original=service.generate_gemini
    async def generate(config,facts,references,transport=None):
        return await original(config,facts,references,httpx.MockTransport(handler))
    monkeypatch.setattr(service,'generate_gemini',generate)
    return calls


def generated(fact='soil-ph', explanation='O pH nao foi informado.'):
    return {"insights":[{"kind":"observation","title":"Solo pendente","explanation":explanation,
                         "fact_ids":[fact],"reference_ids":[],"limitations":["Exige revisao local."],"questions_for_farmer":[]}]}


def test_gemini_rest_contract_and_one_call_cache(setup, monkeypatch):
    client, analysis, cfg = setup
    calls=install_fake_gemini(monkeypatch,cfg,generated())
    body={"analysis_id":analysis['analysis_id'],"use_gemini":True}
    first=client.post('/v1/insights',json=body)
    assert first.status_code==200,first.text
    assert first.json()['status']=='checked' and first.json()['generation_mode']=='gemini'
    assert client.post('/v1/insights',json=body).json()['cache_hit'] is True
    assert len(calls)==1


@pytest.mark.parametrize('output,status',[(generated('invented-id'),200),(generated(explanation='O pH e 7.'),200),(generated(),429)])
def test_invalid_generation_or_quota_uses_fallback(setup,monkeypatch,output,status):
    client,analysis,cfg=setup
    calls=install_fake_gemini(monkeypatch,cfg,output,status)
    response=client.post('/v1/insights',json={"analysis_id":analysis['analysis_id'],"use_gemini":True})
    assert response.status_code==200
    assert response.json()['status']=='fallback' and response.json()['model'] is None
    assert 'dummy-gemini-key' not in response.text
    assert len(calls)==1


def test_knowledge_retrieves_only_approved_compatible_chunks(tmp_path):
    document={"id":"synthetic-doc","title":"Solo e agua","url":"https://example.org/synthetic",
              "region":"global","crops":["soja"],"version":"test-v1","reviewed_at":"2026-11-15",
              "review_status":"approved","chunks":[{"id":"synthetic-chunk","section":"Teste","text":"Solo e agua para soja. Exemplo sintetico."}]}
    (tmp_path/'doc.json').write_text(json.dumps(document),encoding='utf-8')
    knowledge=Knowledge(tmp_path)
    assert [r.id for r in knowledge.retrieve('solo agua',['soja'])]==['synthetic-chunk']
    assert knowledge.retrieve('solo agua',['milho'])==[]
    document['review_status']='draft'
    (tmp_path/'doc.json').write_text(json.dumps(document),encoding='utf-8')
    assert Knowledge(tmp_path).chunks==[]


def test_swagger_describes_new_http_contracts():
    schema=main.app.openapi()
    operation=schema['paths']['/v1/insights']['post']
    assert operation['summary'] and operation['description']
    assert '404' in operation['responses'] and '422' in operation['responses']
    assert operation['requestBody']['content']['application/json']['schema']['$ref'].endswith('InsightsRequest')
    assert operation['responses']['200']['content']['application/json']['schema']['$ref'].endswith('InsightsResponse')
    assert schema['components']['securitySchemes']['GeoSafraToken']['name']=='X-GeoSafra-Token'
    assert operation['security'] == [{'GeoSafraToken':[]}]
    assert schema['components']['schemas']['InsightsRequest']['examples']


def test_attempt_budget_is_atomic_and_prompt_change_invalidates_cache(setup,monkeypatch,tmp_path):
    client,analysis,cfg=setup
    store=SnapshotStore(cfg.cache_dir)
    assert store.claim_generation(analysis['analysis_id']) is True
    assert store.claim_generation(analysis['analysis_id']) is False
    first=client.post('/v1/insights',json={"analysis_id":analysis['analysis_id']}).json()
    prompt=tmp_path/'prompt.txt';prompt.write_text('Novo prompt de teste.',encoding='utf-8')
    monkeypatch.setattr(service,'PROMPT',prompt)
    second=client.post('/v1/insights',json={"analysis_id":analysis['analysis_id']}).json()
    assert second['cache_hit'] is False
    assert second['prompt_hash'] != first['prompt_hash']


def test_invalid_approved_knowledge_is_a_documented_503(setup):
    client,analysis,cfg=setup
    cfg.rag_knowledge_dir.mkdir()
    (cfg.rag_knowledge_dir/'bad.json').write_text(json.dumps({"review_status":"approved","region":"global"}),encoding='utf-8')
    response=client.get('/v1/insights/capabilities')
    assert response.status_code==503
    assert response.json()['status']==503


def test_timeout_falls_back_without_retry(setup,monkeypatch):
    client,analysis,cfg=setup
    monkeypatch.setattr(main,'settings',replace(cfg,insights_enabled=True,gemini_api_key='dummy',gemini_model='gemini-test-only'))
    calls=[]
    async def timeout(*args,**kwargs):
        calls.append(True)
        raise httpx.ReadTimeout('simulated')
    monkeypatch.setattr(service,'generate_gemini',timeout)
    body={"analysis_id":analysis['analysis_id'],"use_gemini":True}
    assert client.post('/v1/insights',json=body).json()['status']=='fallback'
    assert client.post('/v1/insights',json=body).json()['cache_hit'] is True
    assert len(calls)==1
