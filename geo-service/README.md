# geo-service (frente B)

FastAPI que consulta a **NASA POWER**, calcula os indicadores climáticos (ETo FAO-56, veranico, geada, calor, chuva extrema, tendências) e roda o **motor de rotação**. O Laravel é o único cliente.

```bash
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --port 8001 --reload     # docs interativas em http://127.0.0.1:8001/docs
```

| Pasta | Conteúdo |
|---|---|
| `app/power/client.py` | cliente POWER: consultas anuais concorrentes, cache em disco, `fill_value → None`, 422/429/5xx |
| `app/climate/eto.py` | FAO-56 Penman-Monteith |
| `app/climate/indicators.py` | ClimateProfile (B3) |
| `app/catalog/*.json` | 11 culturas e 10 modelos de rotação, com fontes ou hipóteses (B4) |
| `app/engine/` | filtros, critérios, seleção, explicação e cenários (B5) |
| `tests/` | testes com série **sintética** (sem internet) |

Variáveis de ambiente: `GEOSAFRA_TOKEN`, `POWER_START_YEAR`, `POWER_END_YEAR`, `POWER_CONCURRENCY`, `POWER_TIMEOUT`, `CACHE_DIR`, `CORS_ORIGINS`.

Para testar contra a NASA de verdade (precisa de internet):
```bash
curl -X POST localhost:8001/v1/climate-profile -H 'content-type: application/json' \
  -d '{"latitude":-18.9186,"longitude":-48.2772,"start_year":2024,"end_year":2025}'
```
