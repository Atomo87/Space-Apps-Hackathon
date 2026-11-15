# geo-service (frente B)

**HTTP de insights implementado:** veja [docs/http-insights.md](docs/http-insights.md). As rotas, schemas e erros estão no Swagger em `/docs`. O motor permanece intacto; a análise agora retorna um ID para solicitar explicações. Sem Gemini, funciona o fallback determinístico.

Esboço da evolução com Gemini e RAG: [docs/rag/README.md](docs/rag/README.md). Inclui arquitetura, prompt, contrato de saída, exemplos sintéticos e critérios de validação. A integração não está ativa e não altera o motor.

## Bancada de testes desta versão

No PowerShell, dentro de `geo-service1/geo-service`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1
```

Abra **http://127.0.0.1:8002/test**. A porta 8002 distingue este serviço da versão anterior em 8001. Para usar 8001, encerre o outro servidor e informe `-Port 8001`.

O script usa um ambiente Python válido já existente. Uma `.venv` copiada de outro computador pode estar inválida; ela é preservada. `-Install` prepara `.venv-local` quando necessário e instala as dependências desta versão, incluindo h5py e rasterio. Sem essas bibliotecas, algumas leituras Earthdata podem não funcionar. `-PythonPath` permite escolher explicitamente outro executável.

Fluxo da bancada:

1. Informar ponto e período POWER; carregar catálogo.
2. Consultar POWER, obrigatório para a análise.
3. Consultar relevo, vegetação, estresse e Earthdata conforme necessário. As fontes complementares têm checkbox para inclusão na análise.
4. Informar solo, histórico, prioridades e restrições.
5. Comparar rotações e conferir diagnóstico, evidências, critérios, conflitos, lacunas e descartes.

As consultas complementares usam os períodos configurados no servidor, não os anos do formulário POWER. Alterar a localização invalida todos os resultados; alterar o período invalida POWER; alterar o polígono invalida relevo. Falha numa atualização remove o dado anterior dessa fonte, evitando reutilização silenciosa.

O campo de token é do serviço GeoSafra (`GEOSAFRA_TOKEN`), não da NASA. A opção de lembrar salva somente com consentimento explícito em `localStorage` deste navegador/origem. Desmarcar remove o valor salvo. `EARTHDATA_TOKEN` continua exclusivamente no servidor; nenhum segredo do `.env` é embutido na página.

O motor do sênior foi preservado. Esta bancada usa o contrato mensal, não os módulos diários, decêndios ou avaliação de cultivo planejado da outra pasta. NDVI/estresse/Earthdata aparecem principalmente como evidências; relevo pode alterar a nota de erosão conforme o motor existente.

Testes:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-windows.ps1 -Test -PipeLoop
node .\tests\test_testbench.cjs
```

O modo de pipe é exclusivo dos testes Windows com loopback bloqueado. Os testes usam dados sintéticos e transporte em memória; não comprovam disponibilidade das APIs externas.

---

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
