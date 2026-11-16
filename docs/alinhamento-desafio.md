# Alinhamento com o desafio — NASA Space Apps 2026

Para cada pedido do desafio *"Virada no Campo: adaptando fazendas com dados da NASA"*, este documento mostra **onde** o GeoSafra o atende. Também lista o que ainda **não** foi feito, para a equipe falar disso com honestidade na apresentação.

Legenda: ✅ atendido · 🟡 parcial · ⏭️ próxima fase

## Objetivo central

| Pedido | Status | Onde |
|---|---|---|
| Ferramenta de apoio à decisão que combina observações da NASA com solo local, características das culturas e prioridades do produtor | ✅ | Cadastro do talhão (`Fields/Form.vue`): solo, histórico, prioridades e restrições · motor `geo-service/app/engine/` |
| Ajudar a explorar rotações que melhorem a saúde do solo e a resiliência ao clima e à água | ✅ | Aba **Comparar**, com 10 critérios ([motor.md](motor.md)) |
| Comparar **pelo menos três estratégias, incluindo a atual** | ✅ | Estratégia A (atual) + até 3 alternativas com diversidade garantida (Jaccard) |
| Para cada estratégia: **por que** foi sugerida, **evidências**, **benefícios**, **lacunas de informação** e **riscos para revisão local** | ✅ | `StrategyCard.vue`: `rationale`, `evidences` (com dataset e período), `benefits`, `information_gaps`, `local_review_risks`, `conflicts` |
| Apoiar, **sem substituir**, o julgamento do agricultor | ✅ | Aviso fixo em todas as análises, aceite no cadastro da conta, seção "Onde o seu julgamento é essencial", selo de baixa confiança e feedback "faz sentido / precisa de ajuste" |

## Dados da NASA

| Conjunto | Status | Uso |
|---|---|---|
| **NASA POWER** (diário, 2005–2025) | ✅ | Temperatura, chuva, umidade, vento, radiação, pressão e umidade do solo (GWETROOT/GWETTOP) → ETo FAO-56, balanço hídrico, veranicos, geada, calor, chuva extrema, tendências |
| **SRTM** (elevação, ~30 m) | ✅ | Declividade do talhão, classe de relevo (Embrapa) e fator LS da RUSLE no risco de erosão (`geo-service/app/terrain/`) |
| **MODIS** (NDVI MOD13Q1/MYD13Q1 v061, 250 m, 16 dias, últimos 5 anos) | ✅ | Cobertura verde mês a mês (P10/P50/P90), meses com pouco verde cruzados com o solo descoberto informado, imagem recente versus o normal e tendência (`geo-service/app/vegetation/`). Lido pelo espelho público da NASA LP DAAC no Microsoft Planetary Computer. Entra no diagnóstico, nas evidências e nas lacunas, **não na nota** |
| **HLS** v2.0 (Landsat 8/9 + Sentinel-2, NDVI 30 m, últimos 2 anos) | ✅ | Verde na escala do talhão, imagem a imagem (máscara Fmask de nuvem/sombra). Vira a referência do calendário e do diagnóstico quando cobre ≥ 10 meses; senão vale o MODIS |
| **MODIS LST** (MOD11A2, temperatura da superfície, 1 km, 8 dias, 3 anos) | ✅ | Linha "Chão quente" no calendário e comparação superfície × máxima do ar (POWER): sinal de solo exposto ou planta sem água. Complementa o ECOSTRESS: cobre todos os meses na escala de 1 km, enquanto o ECOSTRESS mede o estresse a 70 m só nas passagens sem nuvem |
| **MODIS ET/PET** (MOD16A3GF, 500 m, anual, 5 anos) | ✅ | Razão evapotranspiração real/potencial = estresse hídrico observado (baixo/moderado/alto), nas evidências de todas as estratégias |
| **SMAP** (SPL3SMP_E, umidade do solo 9 km, 2 anos) | ✅ | Linha "Solo seco" no calendário (secura relativa ao próprio solo), último mês contra o normal (`geo-service/app/earthdata/`, OPeNDAP Earthdata Cloud) |
| **ECOSTRESS** (ECO_L4T_ESI, 70 m, 2 anos) | ✅ | Índice de estresse evaporativo no próprio talhão, passagem a passagem (só sem nuvem), nas evidências |
| **GRACE/GRACE-FO** (mascons JPL RL06.3 v04, desde 2002) | ✅ | Água total armazenada na região e tendência (Sen + Mann-Kendall); alerta quando a região perde água |
| **GPM IMERG** (chuva mensal 0,1°, desde 2016) | ✅ | Chuva medida por satélite comparada com a do POWER (no exemplo: GPM 1.449 mm × POWER 1.106 mm/ano → alerta para conferir com o pluviômetro) e últimos 12 meses contra a média. Exige que a conta Earthdata tenha aceitado o EULA da GES DISC |

## Condições e dados

| Pedido | Status | Onde |
|---|---|---|
| Relacionar temperatura, umidade do solo, chuva, evaporação e estresse com a vulnerabilidade das culturas | ✅ | Calendário de vulnerabilidade e "Quando a sua lavoura atual fica mais exposta" |
| Explicar termos científicos (evapotranspiração, anomalia de umidade, NDVI, geada, balanço hídrico) | ✅ | Glossário com ícones "?" em toda a interface (`database/data/glossary.php`), mais de 25 termos |
| Explicar a diferença entre satélite e medição de campo, e como combinar as duas | ✅ | Página **Como funciona**, seção 2. A confiança sobe quando o produtor informa análise de solo e mercado |

## Modelagem e incerteza

| Pedido | Status | Onde |
|---|---|---|
| Abordagens estatísticas para padrões históricos | ✅ | Percentis P10/P50/P90, Mann-Kendall e Sen's slope, anomalia dos últimos 3 anos |
| Destacar transições sazonais, solo descoberto e meses de estresse | ✅ | Calendário mensal com níveis 0/1/2 de calor, geada, seca, chuva forte, solo descoberto (histórico), pouco verde (HLS/MODIS) e chão quente (MODIS LST) + cards de NDVI e de calor/água observados |
| Explicar como o modelo trata a incerteza e onde validar localmente | ✅ | Confiança por critério e por estratégia, faixa de nota entre anos secos e chuvosos, lacunas declaradas |
| Por que não há "IA caixa-preta" na escolha | ✅ | Decisão nº 5 do README: o motor é de regras + multicritério, e toda nota é rastreável até um dado e uma regra |
| Harmonizar datasets de resoluções diferentes numa grade comum | 🟡 | Clima, relevo e vegetação são combinados no nível do talhão (ponto POWER ~50 km + grade SRTM 30 m + pixels HLS 30 m, MODIS 250 m/500 m/1 km), sem reamostragem raster |

## Estratégias de rotação

| Pedido | Status | Onde |
|---|---|---|
| Ciclagem de nutrientes, erosão, matéria orgânica, pragas, uso de água, forragem, mercado | ✅ | 9 critérios ajustáveis + segurança climática |
| Alinhar as ideias às prioridades do agricultor | ✅ | Estrelas de 0 a 5 por critério; o ranking muda na hora |
| Explicar fixadoras de N, plantas de cobertura, raízes profundas e tolerantes à seca | ✅ | Termos `fixacao`, `cobertura`, `raiz` e `tolerante_seca` no glossário + explicação de cada critério |

## Mapas e visualização

| Pedido | Status | Onde |
|---|---|---|
| Mapa interativo do talhão | ✅ | `MapPicker.vue` (MapLibre + imagem de satélite): desenho do contorno e cálculo da área |
| Vulnerabilidades no nível do talhão (erosão, estresse hídrico, geada) | 🟡 | Calendário mensal + card de **relevo** (declividade, classe, fator LS). Ainda não há mapa de zonas dentro do talhão |
| Linhas do tempo e controles de cenário (chuva/temperatura) | ✅ | Gráficos de séries anuais e aba **E se…?** (chuva −40% a +20%, temperatura +0 a +3 °C) |

## Design centrado no agricultor

| Pedido | Status | Onde |
|---|---|---|
| Fácil para quem tem pouca experiência técnica | ✅ | Linguagem simples, ícones, celular primeiro, gráficos carregados depois do resumo (conexão fraca) |
| Informar prioridades e restrições (água, equipamento, mercado) | ✅ | Irrigação (mm/dia), equipamentos que faltam, culturas excluídas, com comprador e sem comprador |
| Lembretes de que a ferramenta apoia e não substitui | ✅ | Aviso no rodapé, na comparação e no cadastro da conta |
| Dados do produtor protegidos | ✅ | Conta com login; cada usuário vê só os próprios talhões; exclusão a qualquer momento (LGPD); exemplo público somente leitura |
