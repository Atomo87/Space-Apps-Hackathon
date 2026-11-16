# Contrato B1 — Laravel ↔ geo-service

Base: `GEO_SERVICE_URL` (ex.: `https://geosafra-geo-service.onrender.com`). Cabeçalho `X-GeoSafra-Token: <GEOSAFRA_TOKEN>` quando o token estiver configurado.
Erros: `application/problem+json` (RFC 9457), com `detail` em português. Validação: HTTP 422 do FastAPI (`detail` é uma lista).

| Método | Rota | Uso | Tempo típico |
|---|---|---|---|
| GET | `/health` | vivo? / ping anti-sono | < 1 s (até ~60 s ao acordar no Render) |
| GET | `/v1/catalog` | culturas, pragas, equipamentos, modelos | < 1 s |
| POST | `/v1/climate-profile` | consulta a NASA POWER e calcula indicadores | 10–90 s sem cache; < 1 s com cache |
| POST | `/v1/terrain` | elevação SRTM → declividade e fator LS | 1–5 s sem cache; < 1 s com cache |
| POST | `/v1/vegetation` | NDVI MODIS 250 m + HLS 30 m → cobertura verde do talhão | 20–60 s sem cache; ~3 s com cache |
| POST | `/v1/earthdata` | SMAP + GPM IMERG + ECOSTRESS + GRACE-FO (exige `EARTHDATA_TOKEN`) → `{smap, gpm, ecostress, grace, notes}`; cada parte pode vir `null` com o motivo em `notes` | 40–90 s sem cache; ~5 s com cache |
| POST | `/v1/stress` | MODIS LST + MODIS ET/PET → calor da superfície e estresse hídrico observados | 5–30 s sem cache; ~2 s com cache |
| POST | `/v1/analysis` | diagnóstico + estratégias A–D | < 1 s |

## POST /v1/vegetation

```json
{ "latitude": -18.9, "longitude": -48.55 }
```
1. Busca STAC (`modis-13Q1-061` no Microsoft Planetary Computer): as composições de 16 dias de Terra (MOD13Q1) e Aqua (MYD13Q1) dos últimos `NDVI_YEARS` anos (padrão 5) que cobrem o ponto.
2. Lê o NDVI e a confiabilidade do pixel de 250 m em cada composição (`/api/data/v1/item/point`, 8 em paralelo). Só entram pixels de confiabilidade 0 ou 1 (sem nuvem e sem neve).

| Campo | Conteúdo |
|---|---|
| `monthly[12]` | `p10`, `p50`, `p90` do NDVI, `n` de imagens válidas e `level` 0/1/2 (pouco verde: P50 < 0,40; muito pouco: < 0,30) |
| `low_green_months`, `peak`, `trough` | meses com pouco verde, mês mais verde e menos verde |
| `recent` | média das 3 últimas imagens válidas, anomalia em relação à mediana do mês e se ficou abaixo do P10 |
| `trend` | Sen's slope por ano + Mann-Kendall da média anual (só anos com ≥ 15 imagens válidas) |
| `series` | todas as observações válidas (`date`, `ndvi`) para o gráfico |
| `coverage`, `thresholds`, `dataset`, `citation`, `source_note`, `failed_requests` | rastreabilidade |

Além disso, `hls` traz o mesmo resumo para o **HLS v2.0** (HLSL30 + HLSS30, NDVI de 30 m dos últimos `HLS_YEARS` anos, só pixels sem nuvem/sombra/água pela Fmask) ou `null` se faltar imagem; a falha do HLS não derruba a resposta.

## POST /v1/stress

Mesmo corpo de `/v1/vegetation`. Resposta: `{ "lst": {...} | null, "et": {...} | null, "notes": [] }` — cada parte é independente; HTTP 502 só se as duas falharem.

| Campo | Conteúdo |
|---|---|
| `lst.monthly[12]` | temperatura diurna da superfície (MOD11A2, ~10h30, 1 km): `p50`, `p90`, `% de semanas ≥ 40 °C`, `level` 0/1/2 (≥ 35 °C / ≥ 40 °C) |
| `lst.hot_months`, `lst.hottest` | meses com mediana ≥ 35 °C e o mais quente |
| `et.yearly[]` | ET e PET anuais em mm (MOD16A3GF, 500 m) e a razão ET/PET |
| `et.et_mm`, `et.pet_mm`, `et.ratio`, `et.stress` | médias e estresse hídrico observado: alto (< 0,25), moderado (< 0,45), baixo |

Os valores por imagem ficam em cache em disco (`cache/planetary/<coleção>_<lat>_<lon>.json`): reprocessar só busca as composições novas. Falha (catálogo vazio, mais da metade das leituras com erro ou menos de 12 imagens válidas) → HTTP 502. O Laravel trata o NDVI como **opcional**, assim como o relevo.

## POST /v1/terrain

```json
{ "latitude": -18.9186, "longitude": -48.2772, "boundary": { "type": "Polygon", "coordinates": [[[-48.2812, -18.9156], "..."]] } }
```
Amostra uma grade 5 × 5 de elevação **SRTM GL1 (~30 m)** sobre o contorno do talhão (ou um quadrado de 300 m no ponto) pela API pública OpenTopoData.

| Campo | Conteúdo |
|---|---|
| `slope_pct` | declividade média, P90 e máxima (%) |
| `elevation_m` | altitude mínima, máxima e média |
| `relief_class` | classe Embrapa: plano, suave ondulado, ondulado, forte ondulado, montanhoso, escarpado |
| `ls_factor`, `ls_relative` | fator topográfico da RUSLE e razão em relação a um relevo de 3 % (1,0 = neutro) |
| `slope_length_assumed_m` | comprimento de rampa assumido (100 m, hipótese) |
| `dataset`, `resolution_m`, `source_note`, `citation`, `fetched_at`, `grid` | rastreabilidade |

Falha → HTTP 502 `problem+json`. O Laravel trata o relevo como **opcional**: guarda `null` e a análise segue (o motor registra a lacuna).

## POST /v1/climate-profile

```json
{ "latitude": -18.9186, "longitude": -48.2772, "start_year": 2005, "end_year": 2025 }
```
Resposta: **ClimateProfile**. Exemplo completo (série **sintética**, não é dado da NASA): [`exemplos/climate-profile.sintetico.json`](exemplos/climate-profile.sintetico.json).

| Campo | Conteúdo |
|---|---|
| `source` | dataset, versão da API, parâmetros com **unidade e nome longo**, período, local, `fetched_at`, mensagens, opcionais ausentes, nota de resolução, citação |
| `monthly[12]` | chuva (média, P10/P50/P90 e por ano), ETo (média e por ano), balanço, Tmax/Tmin/Tmédia, dias de calor por limiar (28–42 °C), probabilidade de geada por limiar (−2 a 6 °C), maior sequência seca, dias de chuva extrema, umidade do solo |
| `season` | maior veranico por safra (out–mar), % de safras com ≥ 10 e ≥ 15 dias |
| `extremes` | P95 dos dias chuvosos, máxima de 1 e de 5 dias |
| `yearly`, `trends`, `recent` | séries anuais, Sen's slope + Mann-Kendall, anomalia dos últimos 3 anos |
| `calendar[12]` | níveis 0/1/2 de calor, geada, seca e chuva forte |
| `confidence` | valor (0–0,6 para dado em grade) e notas |

O Laravel guarda esse JSON em `field_analyses.climate` (o relevo em `field_analyses.terrain` o NDVI em `field_analyses.vegetation` e o estresse em `field_analyses.stress`) e os reenvia em `/v1/analysis`.

## POST /v1/analysis

Corpo (ver [`exemplos/analysis-request.json`](exemplos/analysis-request.json)):

```json
{
  "climate": { "...": "ClimateProfile" },
  "terrain": { "...": "resposta de /v1/terrain ou null" },
  "vegetation": { "...": "resposta de /v1/vegetation ou null" },
  "stress": { "...": "resposta de /v1/stress ou null" },
  "earthdata": { "...": "resposta de /v1/earthdata ou null" },
  "field": { "latitude": -18.9186, "longitude": -48.2772, "area_ha": 48.5, "irrigated": false, "irrigation_mm_day": null },
  "soil": { "source": "lab_analysis|farmer_estimate|unknown", "texture": "arenosa|media|argilosa|muito_argilosa", "ph_water": 5.6, "v_pct": 55 },
  "history": [{ "crop": "soja", "sown_at": "2024-10-25", "harvested_at": "2025-02-20" }],
  "priorities": { "save_water": 4, "soil_structure": 3, "n_fixation": 2, "erosion_control": 4, "organic_matter": 3,
                  "pest_break": 3, "forage": 2, "extra_income": 4, "market_fit": 3 },
  "constraints": { "excluded_crops": [], "buyer_crops": ["soja"], "no_buyer_crops": [], "missing_equipment": [], "has_livestock": true },
  "scenario": { "rain_delta_pct": 0, "temp_delta_c": 0 }
}
```

Resposta (tipos em `resources/js/types/contract.ts` · exemplo em [`exemplos/analysis.sintetico.json`](exemplos/analysis.sintetico.json)):

| Campo | Conteúdo |
|---|---|
| `disclaimer` | aviso fixo ("apoia, não substitui") |
| `weights[]` | peso usado em cada critério (`climate_risk` = 3, não ajustável) |
| `diagnosis` | calendário com solo descoberto e cultura atual, meses vulneráveis da lavoura atual, destaques com fonte e período, séries para os gráficos, fonte e confiança, cenário aplicado |
| `strategies[]` | A (atual, se houver histórico) + até 3 alternativas: `title`, `focus`, `steps`, `cover_by_month`, `score` (0–100), `score_range` (P10–P90 entre anos), `confidence` (`alta` ≥ 0,7; `media` ≥ 0,5; `baixa`), `low_confidence_badge`, `criteria[10]` (nota, peso, confiança, explicação, delta vs. atual), `rationale`, `evidences`, `benefits`, `information_gaps`, `local_review_risks`, `conflicts` |
| `discarded[]` | modelos eliminados pelos filtros duros e por quê |
| `warnings[]`, `human_judgment[]`, `sources[]` | avisos, onde o julgamento humano é essencial, citações |

## API interna do Laravel (consumida pelo Vue)

Autenticação pela **sessão** do Laravel (cookie, mesma origem) com proteção CSRF: o front-end envia `X-XSRF-TOKEN` com o valor do cookie `XSRF-TOKEN`.
Autorização: só o **dono** do talhão, ou qualquer pessoa no **caso público de demonstração** (leitura e simulação). Erros 401/403/404/419/429 em `problem+json` com `detail` em português.

| Método | Rota | Quem | Descrição |
|---|---|---|---|
| GET | `/api/v1/fields/{id}/status` | dono ou demo | `{status, message, analyzed_at}` |
| POST | `/api/v1/fields/{id}/process[?force=1]` | dono ou demo | processa (síncrono, com lock) |
| GET | `/api/v1/fields/{id}/analysis?rain_delta_pct=&temp_delta_c=&priorities[k]=` | dono ou demo | repassa `/v1/analysis` (cache de 30 min por payload); `priorities` opcional simula pesos sem gravar |
| PUT | `/api/v1/farms/{id}/priorities` | dono (logado) | grava os pesos 0–5 |
| POST | `/api/v1/fields/{id}/feedback` | dono ou demo | "faz sentido / precisa de ajuste / não se aplica" |
