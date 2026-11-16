# Matriz de entrega — GeoSafra e desafio NASA

Revisao: 15/11/2026. Versao examinada: geo-service1/geo-service.

## Base oficial e limite da verificacao

Desafio correto: **Field Shift: Adapting Farms with NASA Data**.

Fonte oficial: https://www.spaceappschallenge.org/2026/challenges/field-shift-adapting-farms-with-nasa-data/

O resumo oficial recuperado pelo mecanismo de busca propoe apoio a exploracao de rotacoes, combinando observacoes NASA, informacao local de solo, caracteristicas das culturas e prioridades do agricultor para saude do solo e adaptacao ambiental. A abertura direta da pagina retornou 502 nesta verificacao. Portanto, o resumo esta confirmado por indexacao oficial; nao afirmamos ter auditado todo o regulamento ou a aba completa de recursos.

Como apoio secundario, ha uma reproducao ampliada em https://hackathlone.com/challenges/adapting-farms-with-nasa-data . Seus exemplos e sugestoes nao sao tratados aqui como requisitos obrigatorios confirmados da NASA. A especificacao do senior, incluindo 36 decendios, tambem nao se confunde com regulamento oficial.

## Parecer

**Alinhado ao tema, mas ainda nao pronto para entrega declarada como integralmente veridica e homologada.** Testes comprovam comportamento do software em casos controlados; nao comprovam procedencia de todas as entradas, acuracia agronomica ou funcionamento externo.

| Eixo do objetivo central | Implementacao observada | Estado de entrega | Falta para comprovar |
|---|---|---|---|
| Usar observacoes NASA | Clientes POWER e fontes complementares; indicadores e citacoes | Parcial | Executar consulta real pelo servidor, registrar produto/periodo/local/qualidade e apresentar um caso reproduzivel |
| Incorporar solo local | Formulario de pH, textura e outros atributos; pH/armazenamento entram em regras | Parcial | Caso real com origem/data da analise; nem todos os campos informados alteram calculos |
| Incorporar caracteristicas de culturas | Catalogo com Kc, faixas termicas/pH, residuos e pragas | Bloqueio cientifico | Catalogo declara hipoteses; faltam referencias especificas por atributo e validacao regional |
| Incorporar prioridades do agricultor | Pesos e restricoes de culturas, equipamentos e mercado | Implementado tecnicamente | Conferir com usuario/caso real e mostrar efeito das prioridades nas alternativas |
| Explorar rotacoes | Geracao, filtros, pontuacao, diversidade e comparacao com historico informado | Parcial | Demonstrar alternativas viaveis num caso real; revisar filtros e justificativas agronomicas |
| Apoiar saude do solo e resiliencia | Criterios de cobertura, estrutura, agua, nutrientes e clima | Exploratorio | Indicadores heuristicas nao comprovam ganho real, reducao medida de erosao ou sucesso do cultivo |

## Recursos adicionais do projeto, sem transformar sugestoes em obrigacoes

| Recurso | Estado real |
|---|---|
| Explicacoes/evidencias/lacunas | Presentes; afirmar existencia de regra nao valida sua ciencia |
| Historico e anos atipicos | Comparacao de chuva entre janelas com mediana/MAD; nao previsao, normal oficial ou significancia estatistica |
| Cenarios de chuva/temperatura | Exploratorios, alteram serie; nao sao observacoes reais do futuro |
| Gemini/RAG | Adaptador existente; corpus aprovado vazio e geracao livre restrita. Nao e assistente agronomico completo nem modelo treinado nos dados |
| HTTP/Swagger | Implementados e cobertos por testes em memoria; execucao real no navegador ainda nao homologada |
| Fontes complementares | Clientes presentes, mas h5py e rasterio ausentes no ambiente examinado; nao declarar todos os satelites operacionais |
| Mapa de vulnerabilidade do talhao | Nao homologado como mapa espacial completo; ponto/bbox e indicadores regionais nao substituem detalhamento intratalhao |

## Politica: sem mocks na aplicacao

O endpoint sintetico, gerador em app/ e botao de demonstracao foram removidos. Perfis antigos marcados source.demo sao rejeitados. Dados artificiais continuam somente em tests/ para verificacoes automatizadas; nao sao carregados no produto nem apresentados como observacoes NASA.

Cache de resposta verdadeira pode ser usado desde que preserve proveniencia e periodo. Nao substituir falha externa por numeros inventados. Campos manuais exigem origem declarada. ETo e balanço sao grandezas calculadas; scores e limiares sao regras de modelo, nao medicoes. A autenticacao da procedencia dos perfis enviados pelo navegador ainda nao esta resolvida.

## Criterios concretos para aceitar a entrega

1. Servidor identificado e acessivel: /health, /test, assets e /docs na mesma porta.
2. Instalacao limpa com dependencias das fontes efetivamente utilizadas. Fontes nao homologadas devem ficar explicitamente indisponiveis.
3. Um caso de campo real consentido, com periodo/local da consulta NASA e solo informado com origem; identificar lacunas sem inventar valores.
4. Atributos essenciais do catalogo usados nesse caso com referencias rastreaveis e revisao tecnica. Restringir culturas/criterios se necessario, em vez de alegar validacao geral.
5. Comparacao reproduzivel da rotacao atual com alternativas, mostrando prioridades, evidencias, conflitos e revisao local. O parecer isolado de uma cultura nao substitui a exploracao de rotacoes.
6. Roteiro real executado no computador de apresentacao, relatorio HTTP aprovado, revisao visual e lista franca de limitacoes. Consulta de fontes em testes simulados nao atende este criterio.

Sequencia recomendada: resolver execucao/dependencias; homologar POWER real; selecionar caso e culturas com dados comprovaveis; revisar catalogo; executar comparacao/parecer; finalizar apresentacao. Ampliar Gemini ou integrar todos os satelites nao e prioridade enquanto esses pontos estiverem abertos.
