# Prontidao de entrega — GeoSafra

Data: 15/11/2026. Escopo: geo-service1/geo-service, revisao interna do codigo e execucao dos testes. Nao e homologacao independente.

## Parecer

**Candidato a demonstracao tecnica; entrega ainda nao homologada.** Nao considerar pronto para uso agronomico real ou producao multiusuario.

O fluxo implementado vai das fontes ambientais ao parecer por agua/clima/pH, comparacao entre safras, ranking de rotacoes e explicacoes rastreaveis. Ha contratos HTTP e Swagger. Isso comprova implementacao, nao adequacao agronomica nem disponibilidade das fontes em uma apresentacao real.

## Evidencias desta revisao

- Suite Python: 90 aprovados, um aviso existente de deprecacao Starlette/httpx.
- JavaScript: testes simulados de fontes, erros, invalidacao, token, parecer e comparacao temporal aprovados; repetidos apos limpeza da interface.
- check-startup.py executado: arquivo app/main.py da geo-service1 confirmado e rotas /test, /health, /v1/cultivation-assessment e /v1/insights presentes.
- Dockerfile corrigido para incluir docs/rag e knowledge; .venv-local excluida do contexto. Imagem nao construida nem executada nesta revisao.
- Iniciador Windows confere o aplicativo antes de chamar Uvicorn, usa caminho explicito e reload opcional.
- Removido trecho duplicado de renderizacao temporal no cartao POWER; tabela permanece no parecer.

## Pendencias que bloqueiam a homologacao da demonstracao

1. **Execucao real:** houve relatos de 404 e WinError 10013. Conferir o processo acessivel pelo navegador, com 200 em /test e carregamento dos assets. Presenca da rota no codigo nao encerra este problema. A inspeção do navegador pela ferramenta falhou; nao foi possivel homologar visualmente.
2. **Fluxo real completo:** carregar catalogo, consultar POWER, avaliar um cultivo, comparar rotacoes e obter fallback no mesmo servidor. O transporte externo nao foi exercitado nesta revisao. Testes usam dados sinteticos e/ou transporte simulado.
3. **Apresentacao honesta:** tratar as notas como heuristicas historicas; nao prometer safra prospera, produtividade, lucro, previsao meteorologica, erosao medida ou cobertura integral da especificacao do senior.

## Limites funcionais para explicar na entrega

| Parte | Implementado | Limite |
|---|---|---|
| Cultivo | Parecer por agua, clima e pH, com regras e evidencia | Meses aproximados, sem fenologia diaria; faixas e catalogo exploratorios |
| Serie temporal | Chuva de janelas equivalentes, mediana das demais safras, MAD e tolerancia | Minimo cinco outras janelas completas; nao e normal climatologica oficial nem previsao |
| Rotacoes | Regras, filtros, pesos e explicacoes do motor | Nao equivale ao calendario completo de 36 decendios descrito pelo senior |
| Sensores | Diagnostico e fatos complementares com escala e periodo | Nem todo dado altera a pontuacao; nao demonstram causalidade |
| RAG | Recuperacao lexical local de documentos aprovados | Corpus aprovado vazio; nao ha treinamento de pesos do Gemini |
| Gemini | Adaptador opcional, limite e fallback | Texto livre bloqueado; unica proposicao gerada aceita e ausencia de pH verificada. Nao vender como assistente agronomico geral |
| HTTP/Swagger | Endpoints, schemas e erros documentados | Opcionais ambientais ainda usam dicionarios; tipagem completa e uma evolucao necessaria |

## Pendencias antes de producao

- Autorizar cada analise pelo proprietario no Laravel; token compartilhado autentica servico, nao produtor.
- Autenticar procedencia dos perfis ambientais; snapshot garante integridade local, nao origem NASA.
- Revisar catalogo, limiares e recomendacoes com responsavel agronomico; integrar regras regionais/ZARC quando aplicavel.
- Curar documentos RAG com versao, escopo e revisao; melhorar recuperacao contextual antes de ampliar geracao.
- Armazenamento compartilhado e persistente, quotas por usuario, estados de tarefa, recuperacao e observabilidade. SQLite/TTL e teto por banco sao de prototipo.
- Instalar e verificar dependencias em ambiente limpo; atualmente o iniciador pode aproveitar o ambiente do projeto antigo.
- Homologar imagem Docker e chamadas reais NASA/Gemini, sem incluir credenciais no pacote.

## Roteiro de homologacao manual

No diretorio desta versao, executar `./start-windows.ps1 -Port 8010`. Confirmar a mensagem do check-startup e a mensagem Uvicorn da mesma porta. Abrir http://127.0.0.1:8010/test e http://127.0.0.1:8010/docs.

Carregar catalogo, selecionar o exemplo de local e consultar POWER com um historico suficientemente longo (por exemplo, 2015–2025). Selecionar cultura e datas, avaliar primeiro sem pH e depois com pH informado. Verificar lacuna de solo no primeiro caso, evidencia no segundo e tabela de safras. Ano futuro ausente deve permanecer sem previsao. Comparar rotacoes e obter insights sem Gemini. Falha de fonte deve ser visivel sem reutilizar dados anteriores silenciosamente.

Somente marcar demonstracao como homologada apos executar esse roteiro no computador da apresentacao e registrar o resultado. Esta revisao nao executou esse roteiro real e nao marca a entrega como concluida.

## Verificador HTTP executavel

O iniciador aceita `-Verify -Port 8010` para verificar o servidor ja aberto. Adicionar `-LivePower` executa consulta real POWER (ou cache real do servidor), parecer, criacao/recuperacao de snapshot e fallback, sem chamar Gemini. Usar em outro terminal enquanto o servidor permanece aberto:

```powershell
.\start-windows.ps1 -Verify -LivePower -Port 8010
```

O resultado fica em `docs/homologacao-http.json`. Relatorio sem credenciais ou corpo de erros externos. Estado `blocked` nao pode ser apresentado como homologacao concluida; `http_smoke_passed` nao inclui consulta real e `http_flow_passed` nao substitui revisao visual ou agronomica.

A tentativa nesta sessao retornou ConnectError na porta 8010; nenhuma consulta NASA foi realizada por esse verificador. Suite apos inclusao: 92 testes aprovados, um aviso de deprecacao. Os dois testes novos conferem identificacao de servidor incorreto e ausencia de vazamento de detalhes de erro; nao sao chamadas externas.
