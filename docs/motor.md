# Motor de rotação (B5) — regras

Código: `geo-service/app/engine/`. Determinístico e explicável: toda nota é rastreável até um dado e uma regra.

## 1. Rotação atual
Janela de 12 meses terminando na colheita mais recente do histórico. Os meses com ≥ 15 dias sem cultura contam como **solo descoberto**.

## 2. Candidatas
10 modelos do Cerrado em `catalog/templates.json`, com consórcio (milho + braquiária) e etapas de cobertura na seca (sem checagem hídrica, porque a planta já está estabelecida).

## 3. Filtros duros (eliminam e explicam)
1. Cultura excluída pelo produtor.
2. Equipamento que falta (ex.: semeadora de sementes miúdas).
3. Temperatura média do mês abaixo da temperatura-base da cultura.
4. Geada ≥ 30% dos anos (cultura sem tolerância) ou ≥ 50% (tolerância baixa).
5. **Água:** falta mais de 50% da ETc em ≥ 50% dos anos (balanço mensal com água armazenada no solo). *Calibrado de forma mais branda que o "×1,2" do doc 06, que eliminava o milho safrinha, padrão na região.*
6. pH abaixo do mínimo − 1,0 ou acima do máximo + 0,5 (sem correção viável).
7. Mesma família botânica em sequência quando ambas hospedam uma doença de sequência (mofo-branco, nematoide-de-cisto, cigarrinha). Ex.: **soja → feijão**.

## 4. Critérios (0–100)
| Critério (peso = estrelas do produtor) | Cálculo |
|---|---|
| Uso de água | balanço mensal **ano a ano**: ETc = ETo × Kc (inicial/médio/final) × fração do mês; oferta = 0,8 × chuva + irrigação + água no solo (40/70/100/110 mm conforme a textura). Nota = 100 × (1 − 1,6 × déficit mediano), com bônus para cultura tolerante à seca em região de veranico. P10–P90 entre os anos = faixa da nota |
| Estrutura | raiz profunda +25, média +12, rasa +5; +10 se misturar pivotante e fasciculada; −5 por mês sem planta viva |
| Nitrogênio | crédito de N do catálogo; 120 kg/ha = 100 |
| Erosão | proteção da chuva erosiva: P = Σ (chuva² do mês × cobertura) / Σ chuva². Cobertura: cultura 1,0; dormente 0,8; palhada 0,4–0,7 (C:N); mês de semeadura 0,5. **Relevo (SRTM):** nota = 100 × [1 − (1 − P) × LS/LS₃%], com LS da RUSLE (S de McCool 1987; L de Wischmeier & Smith 1978, rampa de 100 m) limitado a 0,4–2,5 × o de um relevo de 3 %. Sem relevo, LS/LS₃% = 1 e a confiança cai (×0,85 em vez de ×0,95) |
| Matéria orgânica | palhada (t/ha) × fator C:N (1,2 / 1,0 / 0,7); 16 = 100 |
| Pragas | pragas-chave = as hospedadas pelas culturas comerciais atuais. Melhor quebra na rotação (supressora 1,0; não hospedeira 0,7; má hospedeira 0,5) × 75, mais a diversidade de famílias (+15/+25), −10 se repetir a mesma cultura |
| Forragem | valor forrageiro nos meses mai–set |
| Renda complementar | índice de mercado das safras comerciais além da principal (hipótese) |
| Mercado | comprador conhecido 100, desconhecido 50, sem comprador 0 |
| **Segurança climática** (peso fixo 3) | 1 − P(perda), combinando geada, calor acima do limite da cultura na fase sensível e veranico, ponderado pela tolerância |

Nota final = Σ (peso × nota) / Σ peso. Confiança = média ponderada das confianças. Abaixo de 0,5 aparece o selo **"Baixa confiança — validar com técnico"**.

## 5. Seleção
A (atual) mais as 3 maiores notas, **com diversidade**: descarta candidatas com Jaccard de culturas > 0,6 em relação a uma já escolhida, ou > 0,3 com o mesmo critério dominante.

## 6. Explicação
Gerada por template a partir dos números: justificativa (contexto do talhão + foco + maior ganho em relação à atual), evidências (texto + dataset + período), benefícios (deltas ≥ 10 pontos, meses a menos de solo descoberto, redução de déficit, N), lacunas (solo, mercado, declividade, resolução, hipóteses do catálogo), riscos para revisão local (catálogo + riscos climáticos ≥ 25%) e conflitos (critério ≥ 70 junto com outro ≤ 35).

Relevo nas explicações: destaque "Relevo …" no diagnóstico (fonte SRTM), risco para revisão local quando a declividade média ≥ 12 % com solo exposto em meses chuvosos, e aviso geral quando ≥ 20 % (forte ondulado).

## 7. Cenários
Chuva × (1 + Δ%); temperaturas + ΔT; dias de calor e geada relidos com o limiar deslocado; ETo × (1 + 0,03 ΔT). Veranicos e chuvas extremas mantidos (limitação declarada na tela).
