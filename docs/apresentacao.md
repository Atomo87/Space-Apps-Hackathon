# Roteiro da demonstração (J2) — 5 minutos

## 1. Problema (30 s)
Uma cultura que melhora o solo num lugar pode, em outro, gastar água demais, trazer doença, não ter comprador ou não caber na janela de plantio. O agricultor decide com pouca informação local de longo prazo.

## 2. O que fizemos (30 s)
O **GeoSafra** pega ~21 anos de clima diário da **NASA POWER** para o ponto do talhão e mostra:
- **quando** o campo fica descoberto;
- **em que meses** a lavoura atual sofre;
- **quais rotações** podem ajudar, com porquê, evidência e grau de confiança.

## 3. Demo ao vivo (2 min 30 s)
1. Celular → página inicial → "o que faz / o que NÃO faz".
2. **Ver exemplo em Uberlândia** (deixe processado antes).
3. **Diagnóstico:** calendário de vulnerabilidade: chuva forte em dez–mar, seca em mai–set, solo descoberto depois do milho safrinha. Toque no "?" de *veranico*. Mostre "Fonte, período e resolução".
4. **Comparar:** A (atual) × B/C/D. Abra "Ver evidências" e "O que não sabemos". Mostre "Opções descartadas" (soja → feijão, mofo-branco).
5. Mude uma **prioridade** (ex.: forragem 5 estrelas) → *Recalcular* → a ordem muda e cada critério mostra o peso.
6. **E se…?** Chuva −30% e +2 °C → as notas de água e de clima caem. Diga que é cenário, não previsão.
7. Volte em "Editar" → informe uma análise de solo e um comprador → a **confiança sobe** (satélite dá a tendência, o dado local calibra).

## 4. Como usamos os dados da NASA (45 s)
- POWER diária (MERRA-2/CERES): T2M, Tmax, Tmin, orvalho, chuva corrigida, vento a 2 m, radiação, pressão e umidade do solo na raiz.
- ETo FAO-56 Penman-Monteith (testada contra os exemplos da FAO), balanço hídrico ano a ano, veranico, geada (≤ 2 °C), dias de calor por limiar da cultura, chuva > P95, tendência Mann-Kendall/Sen.
- Motor **explicável** (regras + multicritério). A estatística entra na faixa P10–P90 entre anos. Não usamos ML caixa-preta para escolher a rotação.

## 5. Limitações e próximos passos (45 s)
- Grade de ~50 km. Próximo passo: **SMAP** (umidade), **HLS/MODIS** (NDVI e solo descoberto real), **NASADEM** (declividade e erosão), **GRACE-FO** (tendência hídrica regional).
- Catálogo com hipóteses marcadas → validar com agrônomos e cooperativas da região.
- O feedback "faz sentido / precisa de ajuste" já é guardado para calibrar as regras.
- **A ferramenta apoia, não substitui, o agricultor e o técnico.**

## Perguntas prováveis
- *"Por que não IA?"* A escolha precisa ser auditável. Usamos estatística para o diagnóstico e a incerteza, e regras explicáveis para a recomendação. ML entra depois, com dados rotulados (produtividade).
- *"E se o talhão for pequeno?"* O selo de confiança mostra isso, e o dado local tem prioridade.
- *"De onde vêm os números das culturas?"* Kc do FAO-56. O resto está no catálogo, com fonte ou marca de hipótese.
