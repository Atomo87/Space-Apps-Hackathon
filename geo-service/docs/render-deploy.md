# Render — API para desenvolvimento do frontend

## Estado

Configuracao preparada, ainda nao publicada. O diretorio local nao possui repositorio Git vinculado e a conexao de navegador nao deu acesso ao painel Render nesta sessao. Nenhuma URL de servico publicado foi comprovada. Nao enviar .env, tokens, ambientes virtuais ou cache ao repositorio.

## Implantacao

1. Enviar o conteudo de geo-service1/geo-service para o repositorio escolhido.
2. No Render, criar Web Service ligado ao repositorio, runtime Docker. Se o repositorio incluir a estrutura completa do projeto, usar Root Directory geo-service1/geo-service. Dockerfile: ./Dockerfile; Docker Context: diretorio raiz do servico.
3. Health Check: /health. Plano free para este ambiente de desenvolvimento; nao selecionar plano pago sem decisao explicita.
4. Alternativa: Blueprint com render.yaml, se essa pasta for a raiz do repositorio. Para monorepo, adaptar rootDir ao caminho real antes da sincronizacao.
5. Gerar/configurar GEOSAFRA_TOKEN no Render (Blueprint gera automaticamente). Manter REQUIRE_VERIFIED_PROFILES=true e INSIGHTS_ENABLED=false. Gemini nao e necessario para construir o frontend.
6. CORS_ORIGINS deve conter a origem exata do frontend. O Blueprint permite localhost/127.0.0.1 nas portas 5173, 3000 e 8000. Adicionar a URL HTTPS real do frontend quando existir, sem barra final. Nunca usar token Earthdata/Gemini no navegador.
7. EARTHDATA_TOKEN e opcional para fontes autenticadas; configurar somente no painel Render, nao no repositorio. Sem ele, essas fontes continuam indisponiveis. Docker instala requirements.txt, incluindo h5py/rasterio; o build ainda precisa ser comprovado nos logs.

## Entrega ao desenvolvedor frontend

Compartilhar URL base do servico e /docs. Compartilhar token do servico por canal privado; o token nao deve ser commitado ou incorporado em um frontend publico. Preferir proxy Laravel, que guarda o token no backend. A bancada /test permite digitacao manual para testes.

Fluxo: GET /v1/catalog; POST /v1/climate-profile; enviar resposta completa como climate (inclusive _receipt) em POST /v1/analysis ou POST /v1/cultivation-assessment. Manter latitude/longitude identicas. Para insights, POST /v1/insights com analysis_id e use_gemini=false. Interpretar erros por status HTTP e detail.

Frontend nao deve alterar perfis ambientais recebidos; opcoes de chuva/temperatura usam scenario. Consultar novamente a fonte se recibo expirar ou perder validade.

## Persistencia deste ambiente

Servico free usa cache/SQLite efemeros em /tmp/geosafra-cache. Reinicio ou novo deploy pode perder snapshots e recibos; IDs antigos passam a retornar 404/422 e exigem nova consulta. Nao usar para historico permanente ou multiplas instancias. O servico pode ficar inativo e demorar a responder apos um periodo sem uso. Nao representa ambiente de producao multiusuario.

## Conferencia apos publicar

- /health retorna 200.
- /test e assets retornam 200, e /docs mostra /v1/cultivation-assessment, /v1/catalog/evidence e /v1/delivery-progress.
- /v1/catalog sem token retorna 401 e com token retorna 200.
- /v1/data-readiness mostra dependencias e exigencia de recibos, sem revelar credenciais.
- Origem permitida recebe cabecalhos CORS; origem estranha nao recebe permissao.
- Consultar POWER real e executar parecer/analise com recibo no mesmo servico. Nao marcar deploy como homologado apenas por health=ok.

Referencias: https://render.com/docs/deploy-fastapi e https://render.com/docs/blueprint-spec .
