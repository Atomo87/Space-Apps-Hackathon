# Contrato HTTP para o frontend — análises e insights

Cada item de `factors` no parecer inclui `parameter_evidence` e `validation_status`. Referencias de contexto usam `context_only_not_parameter_validation`, preservando a distincao entre parametros do catalogo, valores publicados e regras do modelo. Nao interpretar existencia de URL como validacao regional.

## Atualizacao: integridade das consultas

`GET /v1/delivery-progress` fornece a matriz interna de aceite, pesos, criterios, pendencias e percentual ponderado. Nao e uma nota oficial do desafio. O indicador e revisao manual datada; detalhes em docs/evolucao-objetivos.md. Solo aceita `sampled_at`, `analysis_provider` e `report_reference`, opcionais, sem comprovar autenticidade do laudo; o parecer preserva `origin_verified=false`.

`GET /v1/catalog/evidence` fornece referencia, secao, data de conferencia, estado por parametro e pendencias de validacao regional. Tambem disponivel como `evidence` no catalogo e `catalog_evidence` nos resultados de parecer/ranking. Conferencia de Kc nao valida pH, pragas, biomassa, N ou resultados financeiros. Veja docs/referencias-catalogo.md.

Por padrao `REQUIRE_VERIFIED_PROFILES=true`. Cada resposta de consulta ambiental inclui `_receipt` com ID, SHA-256 e expiracao. O frontend deve enviar o perfil completo, sem remover ou alterar seus campos. Analises e pareceres conferem o recibo contra o banco local, tipo de fonte e latitude/longitude do talhao. Alteracao, expiracao, outro ponto ou outro servidor sem o mesmo banco retornam 422; consultar novamente resolve recibos expirados. Os recibos usam o TTL de snapshots e retencao maxima de dois mil registros.

`source_verification` informa o resultado por perfil. Isso e integridade local, nao assinatura NASA, autenticacao de contas ou validacao agronomica. O cache de origem e o cliente de consulta do servidor continuam parte da cadeia de confianca. Cenários sao aplicados somente depois da verificacao do perfil original. Solo manual nao recebe selo NASA. Recebimento de fonte opcional com campos ausentes nao significa que seus dados estejam disponiveis.

`GET /v1/data-readiness` informa dependencias instaladas, exigencia de recibos e existencia de credencial Earthdata, sem revelar tokens; nao testa conectividade externa. `check-startup.py` avisa sobre h5py/rasterio ausentes. Instalar com `start-windows.ps1 -Install` antes de homologar essas fontes.

Compatibilidade: integracoes antigas que enviavam JSON sem recibo precisam consultar novamente as fontes. `REQUIRE_VERIFIED_PROFILES=false` e uma opcao explicita de compatibilidade e testes, que retorna `unverified`; nao usar na entrega que exige origem registrada. Os testes de algoritmo desabilitam essa exigencia apenas dentro do processo de teste e usam fixtures artificiais; os testes de proveniencia a habilitam e cobrem adulteracao, local, tipo, expiracao e serializacao numerica do navegador.

Swagger local: **http://127.0.0.1:8002/docs**. O OpenAPI em `/openapi.json` contém os schemas, exemplos de entrada e respostas de erro. Use **Authorize → GeoSafraToken** quando `GEOSAFRA_TOKEN` estiver configurado.

## Fluxo implementado

| Método | Caminho | Entrada | Resposta |
|---|---|---|---|
| POST | `/v1/analysis` | Contrato do sênior: clima, talhão e opcionais | Resultado original + `analysis_id`, `created_at`, `expires_at` |
| GET | `/v1/analyses/{analysis_id}` | ID no caminho | Snapshot do resultado, sem recalcular nem chamar APIs externas |
| GET | `/v1/insights/capabilities` | Sem corpo | Habilitação, configuração, versões, quantidade de trechos aprovados e limites; nunca chaves |
| POST | `/v1/insights` | `analysis_id` e `use_gemini` | Insights, evidências resolvidas, referências e modo de geração |

Não mandar fatos ou referências do navegador para `/v1/insights`. O endpoint rejeita campos extras e carrega o snapshot armazenado pelo servidor. A origem dos dados ambientais recebidos pelo contrato antigo ainda depende da validação do Laravel; o snapshot impede substituição posterior do resultado ao solicitar insights, não comprova por si só a origem de toda entrada.

### JavaScript

```javascript
const headers = {
  'Content-Type': 'application/json',
  'X-GeoSafra-Token': tokenDoServico
};
const analysisResponse = await fetch('/v1/analysis', {
  method: 'POST', headers, body: JSON.stringify(dadosDoFormulario)
});
const analysis = await analysisResponse.json();
if (!analysisResponse.ok) throw new Error(analysis.detail);

const response = await fetch('/v1/insights', {
  method: 'POST', headers,
  body: JSON.stringify({analysis_id: analysis.analysis_id, use_gemini: false})
});
const insights = await response.json();
if (!response.ok) throw new Error(insights.detail);
// Exibir insights.insights e resolver cada fact_id em insights.resolved_evidence.
```

Na bancada, o botão **Obter insights** é habilitado depois de comparar rotações. A checkbox Gemini começa desmarcada. Mudar dados do caso invalida o ID da análise na tela.

## Status e tratamento

- `fallback`: templates determinísticos; `fallback_reason` informa não solicitado, configuração ausente, tentativa já usada/em andamento ou resposta externa rejeitada.
- `checked`: Gemini retornou formato aceito e IDs existentes; **não significa validação científica ou agronômica**. A verificação semântica é parcial.
- `insufficient_evidence`: nenhuma explicação disponível com a evidência atual.
- HTTP **401**: token inválido; **404**: snapshot ausente/expirado/removido; **422**: corpo ou ID inválido; **503**: armazenamento ou base RAG indisponível.
- Falha de cota, timeout ou resposta Gemini rejeitada retorna **200 com fallback identificado**, preservando a comparação de rotações.

Os erros seguem `type`, `title`, `status`, `detail`; validações acrescentam `errors` sem expor o corpo inteiro da requisição. O frontend deve tratar tanto o código HTTP quanto o `status` dos insights.

## Evidência e privacidade

`resolved_evidence` contém IDs, rótulos, valores, unidades, fonte, período, limitações e JSON Pointer no snapshot. O Gemini não fornece os valores exibidos: o backend os resolve. `references` contém apenas trechos realmente citados dentre os recuperados. Não há busca web automática ou referências agronômicas pré-aprovadas nesta entrega.

O registro inicial inclui pH informado/ausente, chuva mensal, notas de estratégias e, quando presentes, declividade e NDVI. Estresse e Earthdata continuam no diagnóstico original; seus valores ainda precisam de normalizadores próprios antes de entrarem no registro de fatos do Gemini.

O adaptador envia fatos selecionados e referências, sem coordenadas exatas, nome, ID do produtor ou credenciais. O snapshot local ainda contém o resultado do motor, inclusive metadados ambientais; aplique a política de dados apropriada ao hospedar.

## Configuração, cache e retenção

Veja `insights.env.example`. Para permitir Gemini, configure `INSIGHTS_ENABLED=true`, `GEMINI_API_KEY` e `GEMINI_MODEL`; o cliente também precisa solicitar `use_gemini=true`. Não foi fixado um modelo ou prometida gratuidade. Não houve chamada real à API nos testes.

Há **uma tentativa Gemini por análise**, inclusive em erro. Cache depende de análise, modelo, modo, habilitação, versão do prompt e versão das referências. Ao editar o prompt, incrementar `PROMPT_VERSION`. Para nova tentativa após falha ou mudança de conhecimento, gerar uma nova análise. Requisição simultânea durante a tentativa pode receber fallback temporário identificado; repetir após a conclusão recupera o resultado em cache, sem nova chamada.

SQLite fica em `CACHE_DIR/insights.sqlite3`. Retenção padrão de 24 horas, configurável entre 1 e 168 horas, com máximo de mil snapshots. O ID deixa de existir quando expira ou é removido. Não é histórico permanente de produtores. Em Render com disco efêmero, reinício/deploy pode perder snapshots; múltiplas instâncias exigem armazenamento compartilhado antes de produção.

O token compartilhado autentica o **serviço**, sem isolamento de contas. Em produção, Laravel deve verificar a propriedade da análise e manter esse token no backend. Não apresentar esta autenticação como autorização por produtor. Configure `CORS_ORIGINS` para um frontend em outra origem; a bancada na mesma origem não precisa dessa configuração.

## Base RAG

Arquivos em `knowledge/` devem ser revisados, ter origem HTTPS, versão, página/seção e estado `approved`. Só entram referências globais e compatíveis com a cultura, porque o contrato atual não informa a região agronômica de forma confiável. Índice lexical SQLite FTS5 em memória, sem embeddings ou treinamento. Mudanças no conteúdo/metadados mudam a versão do conhecimento.

## Validação

Testes HTTP cobrem criação/recuperação, expiração, autenticação, campos extras, fallback, resposta Gemini simulada, IDs inventados, novos números no texto, cota, cache e OpenAPI. Testes JS cobrem solicitação por ID e apresentação das evidências. O transporte Gemini é simulado; APIs externas e fatos agronômicos exigem validação independente.

Documentação oficial usada no adaptador:

- https://ai.google.dev/api/generate-content
- https://ai.google.dev/gemini-api/docs/structured-output


## Correcoes da auditoria ? 15/11/2026

- `/v1/analysis` exige doze meses distintos, indicadores de frio/calor e veranico presentes e pelo menos dois anos completos de chuva/ETo. Historico insuficiente ou formato invalido retorna 422, sem ranking. Esta e uma restricao conservadora do prototipo, nao uma exigencia estatistica de climatologia.
- Ciclos outubro-fevereiro usam outubro-dezembro de um ano e janeiro-fevereiro do seguinte. Comparacoes hidricas exigem anos comuns a todas as etapas. Tolerancia biologica nao reduz o deficit fisico em milimetros.
- `checked` substitui `validated` no contrato e na bancada. O texto livre do Gemini esta bloqueado: a unica proposicao permitida nesta versao e a ausencia de pH, quando conferida pelo servidor. Outras geracoes retornam templates. Esta restricao temporaria evita simular uma validacao semantica geral.
- Falta de prompt ou corpus invalido nao derruba o fallback. Capabilities continua sinalizando corpus invalido com 503, para diagnostico operacional.
- Teto de vinte tentativas Gemini por dia UTC por banco SQLite, compartilhado por todos os snapshots, inclusive falhas. Nao substitui limite por conta no gateway nem protege instalacoes com varios bancos independentes.
- Swagger documenta erros como `application/problem+json`. Multisselecoes sao preservadas ao recarregar catalogo.

A origem dos perfis continua declarada pelo cliente e agora aparece como advertencia explicita no resultado. Autorizacao por produtor, assinatura/autenticacao da origem dos perfis, armazenamento compartilhado e curadoria agronomica permanecem requisitos de implantacao. Nao ha corpus cientifico aprovado nem validacao externa nesta entrega.

Normalizadores complementares implementados: temperatura superficial no mes mais quente (MODIS LST), razao ET/PET (MODIS ET), umidade superficial recente (SMAP), chuva anual media (GPM), ESI mediano (ECOSTRESS) e anomalia de armazenamento regional (GRACE). Os respectivos JSON Pointers, unidades e periodos sao resolvidos no servidor. Metricas ausentes nao sao inventadas. Esta atualizacao substitui a limitacao anterior sobre ausencia desses normalizadores.


## Parecer de cultivo ? POST /v1/cultivation-assessment

Endpoint independente do ranking e do Gemini. Recebe os mesmos campos de AnalysisRequest mais `crop` (slug), `sowing_date` e `harvest_date` ISO. Nao exige historico de cultivos; este nao participa do parecer. Datas aceitas: ciclo entre um e 330 dias. Swagger inclui schemas de entrada/saida, seguranca e erros 422 em problem+json.

Na bancada `/test`, consulte POWER e carregue o catalogo; preencha **Cultura planejada**, **Plantio** e **Colheita estimada**, depois clique **Avaliar cultivo**. Solo, irrigacao e cenario usam os campos do formulario. O parecer mostra fatores, evidencias, regras, fontes e limitacoes.

| Status | Significado |
|---|---|
| favoravel_no_historico | Todos os tres fatores foram classificados como compativeis no rastreio. |
| parcialmente_favoravel | Existe atencao ou falta de pH; agua e clima possuem evidencia minima. |
| limitacoes_relevantes | Pelo menos um fator apresenta limitacao, mesmo que outros dados faltem. |
| dados_insuficientes | Sem fator limitante identificado, mas agua ou temperatura nao permitem concluir. |

As regras v1 sao exploratorias e explicitadas na resposta: tres safras completas minimas para agua; deficit mediano <=10% compativel, >30% limitante. Temperatura abaixo da base do catalogo e limitante; frequencia de frio >=10% ou pelo menos tres dias quentes/mes gera atencao. pH e comparado a faixa do catalogo, sem recomendar corretivos. Esses limiares nao foram validados agronomicamente e nao sao ZARC ou probabilidades de perda.

Janela aproximada por meses, usando o balanco mensal existente; dias informados nao recortam exatamente as series. O ano escolhido nao e previsao: avaliam-se janelas equivalentes nas safras historicas, com virada de ano correta. Nao cobre fases fenologicas, eventos diarios, produtividade ou lucro. Culturas perenes e ciclos longos exigem outro modelo.

Validacao desta entrega: 84 testes Python aprovados e teste JavaScript incluindo requisicao HTTP, renderizacao e invalidacao do parecer. Dados sinteticos e transporte simulado; nao constitui validacao agronomica externa.


## Comparacao temporal de safras

`POST /v1/cultivation-assessment` aceita `anomaly_tolerance_pct` (padrao 20, entre 0 e 100) e devolve `temporal_comparison`. A bancada apresenta tabela por safra logo abaixo dos fatores do parecer. O controle **Tolerancia de chuva (%)** define a tolerancia percentual minima.

Cada linha soma chuva e ETo de meses inteiros da janela equivalente. Para outubro-fevereiro, usa outubro-dezembro do ano inicial e janeiro-fevereiro do seguinte. So considera janelas com chuva e ETo presentes em todos os meses. Os acumulados nao sao os valores parciais do balanco da cultura: a comparacao temporal possui outra finalidade.

Referencia: mediana de pelo menos cinco outras safras completas, excluindo o proprio ano. Faixa de tolerancia: maximo entre percentual configurado vezes mediana, 30 mm e 3 x 1,4826 x MAD. MAD e a mediana dos desvios absolutos em relacao a mediana de referencia. Igualdade com o limite permanece dentro da faixa. Esta e uma regra exploratoria robusta, nao normal climatologica oficial, teste de significancia ou probabilidade de perda.

| Campo | Significado |
|---|---|
| seasons[].classification | dentro_da_faixa, mais_seca, mais_chuvosa, sem_dados ou referencia_insuficiente |
| seasons[].reference_count | Quantas outras janelas completas compoem a referencia |
| seasons[].reference_median_mm | Chuva mediana das demais safras |
| seasons[].rain_difference_pct | Desvio percentual; null quando mediana de referencia e zero ou evidencia insuficiente |
| seasons[].tolerance_mm | Tolerancia efetiva, que pode exceder o percentual configurado |
| seasons[].missing_months | Meses ausentes, com ano calendario correto |
| requested_year_available | Existencia de janela completa para o ano de plantio informado; nao implica referencia suficiente |

A classificacao refere-se somente ao acumulado de chuva. ETo e mostrada como contexto; temperatura, distribuicao diaria, veranicos, produtividade e lucro nao sao classificados aqui. Nenhuma proje??o e preenchida para ano ausente. Cen?rios sao aplicados a toda a serie; nao equivalem a observacoes atuais comparadas com normal nao alterada. O parecer agronomico e a classificacao temporal continuam separados: safra mais chuvosa nao significa cultura mais adequada.

Verificacao: 90 testes Python aprovados (um aviso de deprecacao existente) e testes JavaScript incluindo envio da tolerancia, tabela e aviso de ano ausente. Casos controlados cobrem seca/chuva atipicas, igualdade no limite, referencia zero, serie curta, virada de ano, ETo ausente e alta variabilidade historica. Sem consulta externa nesta etapa.
