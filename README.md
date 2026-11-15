# GeoSafra - API

Backend Python/FastAPI para explorar rotacoes agricolas com dados NASA e informacoes locais. Esta entrega contem somente o geo-service; o frontend pode ser acrescentado pela equipe.

## Render

Blueprint em render.yaml; servico geosafra-geo-service; Root Directory geo-service; runtime Docker; plano free; health /health. O Render instala requirements.txt e publica a porta PORT. Configure credenciais no painel, nunca no Git.

## Integracao

Swagger: /docs. Bancada: /test. Consultar /v1/catalog e /v1/climate-profile; enviar perfil completo com _receipt para /v1/analysis ou /v1/cultivation-assessment, mantendo o ponto original. Insights: /v1/insights com analysis_id e use_gemini=false. Enviar X-GeoSafra-Token quando configurado. Detalhes em geo-service/docs/http-insights.md.

## Estado

104 testes Python e suite JavaScript aprovados na copia de desenvolvimento. Dados sinteticos existem somente nos testes. Consulta externa real e regras agronomicas ainda requerem homologacao. O catalogo possui parametros exploratorios e nao deve ser apresentado como validado regionalmente. Gemini e opcional, restrito e desativado por padrao; corpus RAG aprovado ainda vazio.

SQLite e cache sao efemeros no plano free: reinicio pode invalidar snapshots e recibos. Nao e ambiente de producao multiusuario. Credencial de servico deve ficar no backend Laravel em integracao publica.

## Executar localmente

Na pasta geo-service, executar start-windows.ps1 -Install -AutoPort. Para testes, start-windows.ps1 -Test; a opcao -PipeLoop e especifica do ambiente Windows isolado de desenvolvimento.
