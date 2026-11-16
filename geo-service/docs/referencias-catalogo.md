# Conferencia bibliografica do catalogo

## Contexto de pH e temperatura

Foram consultadas diretamente as paginas oficiais CFIA BIO2021-01, secao 3.5 Habitat, e FAO EcoCrop Zea mays, secao Ecology. URLs constam de app/catalog/evidence.py e sao retornadas pela API.

Essas referencias foram classificadas como **context_only_not_parameter_validation**: a CFIA descreve tolerancia geral de pH da soja, nao um protocolo de pH em agua para o Cerrado. Para milho, EcoCrop diferencia faixa otima de limites absolutos. Temperatura do solo para germinacao nao equivale a temperatura-base fenologica nem a media mensal do ar. Por isso, nenhum desses contextos substituiu numeros do motor ou encerrou a validacao regional.

Os fatores agua/clima/solo agora incluem parameter_evidence e validation_status=exploratory_not_regionally_validated. Os campos mostram valor do catalogo, contexto publicado, fonte/secao e limites de uso, conforme disponivel. A existencia de referencia e a verificacao de procedencia dos dados NASA nao tornam o parecer uma recomendacao agronomica validada.

Data: 15/11/2026. Fonte consultada: FAO Irrigation and Drainage Paper 56, capitulo 6, Tabela 12.

URL: https://www.fao.org/4/x0490e/x0490e0b.htm

Conferidos os Kc existentes de soja, milho-grao, milheto e sorgo-grao. Soja e milheto coincidem com valores tabelados, incluindo o coeficiente inicial do grupo. Para milho, o valor final adotado corresponde a uma extremidade do intervalo publicado; para sorgo, o valor intermediario e uma escolha dentro do intervalo. Essas escolhas ficam explicitas na API. Nao foram modificados os numeros do motor nesta revisao.

A conferencia e bibliografica e restrita ao parametro Kc. Nao comprova calibracao para cultivar/local, identifica fases reais ou valida outros atributos. A referencia descreve condicoes padrao e ajustes conforme desenvolvimento e ambiente. A aproximacao mensal do GeoSafra nao implementa todo esse procedimento.

`GET /v1/catalog/evidence` e `evidence` em `/v1/catalog` mostram a situacao por parametro. Parecer e ranking incluem `catalog_evidence`. Valores mudados nao herdam a conferencia automaticamente. Parametros nao conferidos permanecem `not_verified_in_this_review`; nenhum registro e marcado como regionalmente validado.

## Ambiente local

Criado .venv-local para preparar instalacao independente. Tentativa pip isolada, contra PyPI oficial e requirements-dev.txt, nao obteve distribuicoes de fastapi nesta sessao. Instalacao nao concluida. O iniciador detecta ausencia das dependencias principais e utiliza ambiente existente quando disponivel, em vez de selecionar o ambiente novo vazio. h5py/rasterio continuam nao homologados. Nao declarar fontes complementares operacionais por causa desta tentativa.
