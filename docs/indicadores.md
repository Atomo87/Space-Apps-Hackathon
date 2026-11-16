# Indicadores históricos (B3) — regras documentadas

Fonte: NASA POWER, API diária por ponto, comunidade `ag`, horário solar local (LST), unidades métricas. Período padrão: **2005–2025** (21 anos completos), em consultas **anuais** com cache.

Variáveis: `T2M`, `T2M_MAX`, `T2M_MIN`, `T2MDEW`, `PRECTOTCORR`, `RH2M`, `WS2M`, `ALLSKY_SFC_SW_DWN`, `PS` (obrigatórias) e `GWETROOT`, `GWETTOP` (opcionais: se a API recusar com 422, a consulta é refeita sem elas e a lacuna é registrada).

## Tratamento de dados
- `fill_value` (−999) → `null`, **nunca zero**. As séries são alinhadas pela data.
- Mês com menos de **90%** dos dias válidos não entra nas médias. Entre 90% e 100%, a soma é completada proporcionalmente.
- Um dia sem dado **interrompe** a contagem de dias secos (não assumimos que foi seco).
- A unidade de radiação é lida da resposta (`parameters.ALLSKY_SFC_SW_DWN.units`) e convertida explicitamente. Se for desconhecida, a ETo não é calculada.

## Indicadores
| Indicador | Regra |
|---|---|
| Chuva mensal | soma dos dias válidos. Média, P10, P50 e P90 entre os anos |
| **ETo** | FAO-56 Penman-Monteith diária. `ea` pelo ponto de orvalho (eq. 14), com RH média como alternativa (eq. 19). `G = 0`. Albedo 0,23. Rso pela altitude. Conferida com os Exemplos 8 e 18 do FAO-56 (testes automatizados) |
| Balanço hídrico | chuva média − ETo média (mm/mês) |
| Dias de calor | dias com Tmax ≥ L, para L = 28…42 °C (média por mês). O calendário usa 34 °C. O motor usa o limiar de cada cultura |
| Risco de geada | fração dos anos com ao menos um dia de Tmin ≤ L no mês, para L = −2…6 °C. Referência: **2 °C** (abrigo), porque a folha pode congelar antes de o ar chegar a 0 °C |
| Veranico | maior sequência de dias com chuva < **1 mm**. Por mês e por safra (out–mar). % de safras com ≥ 10 e ≥ 15 dias |
| Chuva extrema | dias acima do **P95** dos dias chuvosos (≥ 1 mm). Máximas anuais de 1 e de 5 dias |
| Tendência | Sen's slope (por década) + Mann-Kendall (p bicaudal) da chuva anual, Tmax e Tmin. Só é citada no diagnóstico se p < 0,1 |
| Anomalia recente | últimos 3 anos × média do período |
| Umidade do solo | média mensal de `GWETROOT` (0–1, modelo MERRA-2) |

## Calendário de vulnerabilidade (0 = baixo, 1 = atenção, 2 = alto)
| Risco | 1 | 2 |
|---|---|---|
| Calor | ≥ 2 dias/mês com Tmax ≥ 34 °C | ≥ 5 dias |
| Geada | P(Tmin ≤ 2 °C) ≥ 10% | ≥ 30% |
| Seca | balanço < −20 mm, ou veranico médio ≥ 7 dias (out–mar) | balanço < −60 mm, ou veranico ≥ 10 dias |
| Chuva forte | ≥ 0,5 dia/mês acima do P95 | ≥ 1 dia |
| Solo descoberto | ≥ 15 dias sem cultura no mês (histórico informado), fora da estação chuvosa | idem, dentro da estação chuvosa |

## Confiança
Dado em grade regional sem calibração local tem teto de **0,6** × cobertura das variáveis principais. Os critérios baseados no catálogo variam de 0,4 a 0,55. Mercado conhecido sobe para 0,8. Análise de solo eleva a confiança do critério de água.
