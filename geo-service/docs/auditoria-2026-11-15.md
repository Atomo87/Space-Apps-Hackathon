# Auditoria e autocrítica — geo-service1

Data: 15/11/2026. Escopo: versão do sênior com bancada, snapshots, API HTTP e insights acrescentados nesta sessão. **Nenhum código funcional foi corrigido nesta auditoria.** Este relatório é uma fotografia do estado atual.

## Parecer

O projeto tem uma integração demonstrável entre dados, motor, HTTP e frontend. Ainda não está pronto para orientar uma decisão agronômica real nem para exposição multiusuário sem controles adicionais. O problema prioritário é confiabilidade da evidência, não aparência da interface.

Os 65 testes existentes passaram novamente, com um aviso de depreciação Starlette/httpx. Os testes JavaScript também passaram. Porém, sondagens adicionais encontraram falhas fora da cobertura atual. Passar na suíte não comprova validade científica ou ausência de bugs.

## Como foi verificado

- Leitura dos módulos do motor, contratos, handlers HTTP, RAG, Gemini, snapshots e frontend.
- Suíte completa em transporte ASGI de memória, usando o runner Windows com pipe.
- Sondagens adversariais com séries sintéticas e diretórios temporários.
- Inspeção do OpenAPI efetivamente gerado e comparação com respostas HTTP.
- Nenhuma chamada real ao Gemini/NASA, nenhuma leitura ou impressão de credenciais e nenhuma mudança nos arquivos de implementação.

## Achados confirmados por execução

### A01 — Bloqueador de confiabilidade: sem clima, notas de água e clima chegam a cem

**Local:** `app/engine/criteria.py`, `step_water`, `crit_water`, `interp_threshold` e critérios climáticos.

**Reprodução:** gerar série sintética, substituir todas as variáveis por valores ausentes, construir perfil e avaliar a rotação atual.

**Resultado observado:** `save_water=100` e `climate_risk=100`. A confiança baixa não torna essa nota correta.

**Causa:** ausência convertida em zero déficit/exposição; percentis vazios usam `or 0.0`.

**Correção recomendada:** propagar estado não avaliável; publicar nota nula e lacuna; impedir ranking favorável fundamentado em clima ausente. Acrescentar regressão específica na geo-service1.

### A02 — Alta: safras que atravessam dezembro misturam anos

**Local:** `app/engine/criteria.py`, `step_water`, leitura de `rain_by_year.get(y)` para todos os meses.

**Reprodução:** disponibilizar somente o ano de 2024 e avaliar uma etapa outubro–fevereiro.

**Resultado observado:** 2024 aparece como ano de plantio válido, apesar de janeiro–fevereiro de 2025 não estarem disponíveis. O código reutiliza os meses de 2024.

**Correção recomendada:** indexar por ano-safra, deslocar o ano ao cruzar dezembro e excluir janelas incompletas; alinhar também as etapas consecutivas da rotação.

### A03 — Alta: o validador Gemini aceita contradição e recomendação disfarçada

**Local:** `app/insights/service.py`, `validate_generated`.

**Reproduções observadas:**

- Fato sintético de pH com valor conhecido; resposta «O pH não foi informado.» com ID existente: aceita.
- Resposta «Esta cultura dispensa irrigação.», rotulada como observação e citando somente pH, sem referência agronômica: aceita.

**Causa:** o validador confirma estrutura, existência de IDs, alguns padrões de texto e referência obrigatória conforme o `kind` declarado pelo próprio modelo. Não confirma suporte semântico da afirmação.

**Correção recomendada:** não chamar esse estado simplesmente de validação factual. Até existir avaliação semântica/revisão suficiente, limitar a geração a paráfrases de proposições estruturadas aprovadas e validar também o tipo de afirmação. Um segundo LLM, sozinho, não resolve a garantia de fundamentação.

### A04 — Alta: o contrato aceita formatos internos que provocam erro de servidor

**Local:** `app/schemas.py`, `AnalysisRequest.climate`; `app/main.py`, `analysis`.

**Resultado observado:** `climate.monthly=[1]` e `climate.monthly="invalid"` passam pela validação externa e produzem HTTP 500. Já `[{}]` produz 422 por um `KeyError` posterior, o que evidencia tratamento inconsistente.

**Correção recomendada:** schemas internos para perfil e fontes opcionais; checar doze meses válidos, números finitos, unidades, períodos e coerência espacial antes de executar o motor. Contratos precisam rejeitar entradas inválidas como erro de cliente, sem depender de exceções acidentais.

### A05 — Média: o fallback depende de componentes opcionais

**Local:** `app/insights/service.py`, criação de `Knowledge` e leitura do prompt antes de escolher o modo.

**Resultados observados com `use_gemini=false`:**

| Condição | HTTP |
|---|---|
| Base sem documentos | 200, fallback disponível |
| JSON inválido na pasta de referências | 503 |
| Arquivo do prompt ausente | 500 |

**Correção recomendada:** construir o fallback independentemente do prompt/índice; degradar esses componentes com aviso e observabilidade. Preservar a análise mesmo quando explicação opcional falha.

### A06 — Baixa: divergência de mídia no Swagger

**Local:** `app/main.py`, `API_ERRORS` e handlers.

**Resultado observado:** Swagger documenta 422 como `application/json`; o endpoint retorna `application/problem+json`.

**Correção recomendada:** alinhar conteúdo e exemplos dos erros ao OpenAPI; acrescentar teste de mídia, não somente presença do schema e status.

## Achados por inspeção

| ID / prioridade | Achado | Efeito | Próxima ação |
|---|---|---|---|
| A07 / Alta antes de multiusuário | Token compartilhado, sem propriedade do snapshot | Um detentor do token e de um ID consegue consultar a análise correspondente; UUID imprevisível não substitui autorização | Laravel deve impor dono/escopo; serviço precisa receber contexto confiável ou ficar restrito ao backend |
| A08 / Alta antes de ampliar Gemini | Limite de uma tentativa por snapshot, sem orçamento global/por usuário | Novos IDs permitem novas chamadas; a regra atual não limita custo total | Orçamento diário, quota por identidade, limite de tamanho e taxa na criação de análises |
| A09 / Alta de integridade | Perfil e fontes completos vêm do cliente como dicionários | Snapshot congela um resultado, mas não autentica a origem NASA das entradas; metadados e local podem ser inconsistentes | Referenciar resultados de fontes por IDs do servidor ou verificar assinatura/estrutura e coerência |
| A10 / Média | `build_facts` atribui o período POWER a todos os fatos | pH informado e NDVI recente podem aparecer com uma janela histórica que não corresponde à sua origem | Metadados temporais por fato; período desconhecido permanece desconhecido |
| A11 / Média | Registro de fatos não incorpora valores de SMAP/GPM/ECOSTRESS/GRACE/LST/ET | Consultas complementares enriquecem o diagnóstico, mas boa parte não chega ao Gemini | Normalizadores por produto com unidade, resolução, período, qualidade e limitação |
| A12 / Média | Consulta RAG usa culturas e termos fixos genéricos | Recuperação não é orientada pela pergunta, restrição ou fase do cultivo; ausência de teste de relevância | Consultas por lacuna/critério, avaliação de recuperação e conjunto revisado de casos |
| A13 / Média | Zero documentos agronômicos aprovados no diretório atual | Há mecanismo RAG implementado, mas não base agronômica operacional | Curadoria pequena e rastreável; não inventar referência para preencher a base |
| A14 / Média | Fallback retorna avisos genéricos e a primeira chuva mensal válida | Não responde suficientemente à pergunta «condições favoráveis para este cultivo nesta janela?» | Selecionar evidências pertinentes à janela e a uma pergunta definida, depois de corrigir o motor |
| A15 / Média | SQLite local, limpeza na abertura e retenção por contagem | TTL lógico não é remoção física agendada; snapshots podem persistir com aplicação ociosa e se perder em disco efêmero | Política explícita, rotina de limpeza e armazenamento compartilhado/durável antes de escalar |
| A16 / Média | Tentativa Gemini registrada antes da chamada, sem estado de conclusão/lease | Uma queda de processo consome a tentativa e não é distinguível de execução ainda em andamento | Estados de job, tempo limite e política de recuperação compatível com controle de custo |
| A17 / Média | `.dict`/`Any` e comentários de prompt não bastam para proteção contra conteúdo recuperado malicioso | IDs válidos ou texto aprovado não garantem que uma inferência seja correta | Tratar referência como dado, limitar ações, testar injeção e exigir revisão das proposições |
| A18 / Baixa | Recarregar catálogo preserva só um `.value` ao reconstruir selects múltiplos | Restrições selecionadas podem ser perdidas | Preservar o conjunto de opções selecionadas e testar esse fluxo |

## Questões agronômicas que permanecem

- Estação chuvosa fixa e resolução mensal do motor da geo-service1.
- Tolerância à seca reduz o déficit numérico calculado; é preciso separar água física de sensibilidade da cultura.
- Erosão continua sendo índice heurístico com LS aproximado e rampa presumida; a expressão «percentual de chuva erosiva protegida» é forte demais para o método.
- NDVI, LST e SMAP ainda possuem classificações que podem representar ausência como nível zero.
- Fontes genéricas/hipóteses do catálogo não validam ganhos de N, palhada, controle de pragas ou mercado.
- Comparações entre produtos podem usar períodos, pixels e horários diferentes; concordância ou diferença exige harmonização e ressalva.

Esses pontos não se resolvem adicionando Gemini. O LLM pode apenas redigir de forma mais convincente uma conclusão incorreta do motor.

## Autocrítica da implementação que acrescentei

1. **Priorizei a integração antes da robustez semântica.** O fluxo HTTP funciona, mas usei `validated` para algo que verifica principalmente forma e IDs. Mesmo com ressalva na documentação, o nome e a fluência do texto podem transmitir confiança excessiva.
2. **Congelei a saída sem resolver a proveniência da entrada.** Expliquei a limitação, mas o snapshot não deve ser apresentado como prova de origem NASA.
3. **O fallback ficou acoplado a prompt e RAG.** Isso contraria o propósito de uma alternativa resiliente. O caso do prompt ausente deveria ter sido coberto antes da entrega.
4. **A cobertura de testes ficou concentrada em contratos e cenários esperados.** IDs inventados e números novos foram testados; contradições com IDs válidos e dados climáticos totalmente ausentes precisavam entrar no conjunto adversarial.
5. **O registro de fatos é estreito e seus períodos são genéricos.** Eu deveria ter separado proveniência e aplicabilidade de cada produto antes de chamar a saída de insight contextualizado.
6. **Preservar a versão do sênior era a instrução recebida, mas não elimina a obrigação de evidenciar bloqueadores.** Mantive o motor intacto; agora a prioridade deve ser corrigir esses casos, com mudanças pequenas e aprováveis tecnicamente, antes de ampliar a IA.

## O que está sólido nesta etapa

- Contratos HTTP novos, Swagger com exemplos, token pelo header e erros estruturados.
- Snapshots, consulta por ID, cache com hashes, expiração lógica e tentativa Gemini deduplicada.
- Gemini desabilitado por padrão, opt-in no cliente e chave somente no servidor.
- Respostas externas e credenciais não são repassadas em erros do adaptador Gemini.
- Fatos numéricos exibidos vêm do snapshot; o modelo não fornece os valores hidratados.
- Ausência de base agronômica é explícita; documentos não aprovados não entram no índice.
- Frontend usa `textContent` e invalida resultados quando o caso muda; testes simulam falhas e persistência opcional do token.

Esses controles têm utilidade real, mas não compensam os achados A01–A04.

## Ordem recomendada de correção

1. **A01/A02:** ausência de dados e ano-safra, com regressões sobre o motor da geo-service1.
2. **A04/A09/A10:** validação interna, vínculo entre fontes e caso, proveniência temporal por fato.
3. **A05/A06:** fallback independente e fidelidade entre HTTP e Swagger.
4. **A03/A14:** restringir proposições geradas e melhorar seleção de evidências; testar contradição e recomendação disfarçada.
5. **A07/A08/A15/A16:** identidade, orçamento e persistência antes de uso multiusuário ou ampliação das chamadas externas.
6. Curar referências, incorporar produtos complementares e fazer avaliação agronômica com casos reais revisados.

## Limites deste parecer

Revisão interna do próprio desenvolvimento, não auditoria independente, pentest, validação científica ou teste de carga. Não foi medido desempenho com corpus grande nem realizado ensaio visual completo em navegador real nesta rodada. As sondagens usam dados sintéticos e não comprovam disponibilidade ou exatidão das fontes externas.


## Atualizacao apos as correcoes

A fotografia acima descreve o estado anterior. Correcoes posteriores nesta mesma data:

| Achado | Tratamento implementado |
|---|---|
| A01 | Analise bloqueada com 422 quando faltam series completas e indicadores; ausencia nao gera ranking favoravel. |
| A02 | Meses apos dezembro usam o ano seguinte; safras incompletas sao excluidas. |
| A03 | Texto livre rejeitado; somente proposicao conferivel sobre ausencia de pH. Status checked substitui validated. |
| A04 | Validacao estrutural dos meses e series; demais falhas de formato no calculo viram 422. Tipagem completa dos opcionais ainda e evolucao necessaria. |
| A05 | Corpus/prompt indisponiveis nao interrompem fallback. |
| A06 | Media type de erros alinhado no Swagger. |
| A08 | Limite global de vinte tentativas/dia UTC por banco; limite por produtor e multi-instancia ainda requerem gateway. |
| A09 | Advertencia explicita de origem declarada. Autenticacao da procedencia continua pendente. |
| A10 | pH sem data nao herda periodo POWER; SRTM usa 2000 e NDVI usa data propria quando disponivel. |
| A18 | Multisselecoes preservadas ao recarregar catalogo. |

Deficit fisico nao recebe mais fator de tolerancia biologica. Explicacao de erosao agora identifica indice heuristico de cobertura, sem prometer percentual de protecao medida.

Permanecem abertos: autorizacao por produtor no Laravel, autenticacao da origem ambiental, curadoria RAG, recuperacao contextual, insights por fase/ciclo, persistencia de producao, fila com estados e validacao agronomica independente. Nao foram declarados resolvidos por documentacao.

Verificacao: 76 testes Python passaram, com um aviso de deprecacao, e bancada JavaScript passou. Inclui onze casos novos para formatos invalidos, ausencia de chuva, virada de ano, contradicoes, fallback independente, teto global e Swagger. Sem chamadas reais a NASA/Gemini.

A11: normalizadores explicitos acrescentados para MODIS LST/ET, SMAP, GPM, ECOSTRESS e GRACE, com unidades e periodos proprios e advertencia de escala/origem. Valores presentes entram em observacao deterministica complementar; nao alteram automaticamente as notas.

Nota operacional: uma execucao intermediaria encerrou no adaptador de named pipes do runner Windows com codigo 0xc0000008. A repeticao integral concluiu com 76 testes aprovados. Isso indica instabilidade do runner isolado e nao foi classificado como corrigido nesta entrega.
