# Evolucao em relacao aos objetivos

Revisao interna: 15/11/2026. Rubrica mvp-acceptance-v1. Nao e nota oficial NASA, acuracia ou cobertura cientifica.

O objetivo central do desafio e explorar rotacoes combinando observacoes NASA, solo local, caracteristicas das culturas e prioridades do produtor, para apoiar saude do solo e resiliencia. Ver docs/matriz-desafio-entrega.md para fonte oficial, limites da recuperacao e distincao entre exigencias e sugestoes. O eixo HTTP/interface e um criterio de entrega do nosso MVP, nao uma exigencia especifica atribuida a NASA.

## Como calcular

Cada criterio de aceite vale uma unidade em seu eixo. Percentual do eixo = criterios completos / criterios do eixo x 100. O total e a media dos percentuais ponderada pelos pesos abaixo. A lista completa, estados e evidencias fica em app/delivery.py e GET /v1/delivery-progress. Revisao manual datada: nao se atualiza sozinha quando um teste passa, servidor inicia ou referencia muda.

| Eixo | Peso | Percentual atual | Principal pendencia |
|---|---:|---:|---|
| Observacoes NASA | 20% | 50% | Dependencias e consulta real homologada |
| Solo local | 10% | 75% | Caso de campo comprovavel |
| Caracteristicas das culturas | 20% | 50% | Referencias dos demais parametros e revisao regional |
| Prioridades do produtor | 10% | 75% | Validacao com produtor num caso real |
| Explorar rotacoes | 20% | 60% | Filtros regionais e comparacao real homologada |
| Saude do solo e resiliencia | 10% | 50% | Conferencia em campo e revisao tecnica dos beneficios |
| Entrega HTTP/interface | 10% | 60% | Navegador e fluxo externo completos homologados |
| **Total ponderado** | **100%** | **58%** | **Ainda nao pronto para entrega homologada** |

## Evolucao desta etapa

A primeira linha de base foi definida nesta etapa, antes da inclusao dos campos de origem do solo: 55,5%. Nao e uma medicao historica das conversas anteriores. Na mesma rubrica, incluir data da coleta, laboratorio/responsavel e referencia do laudo concluiu um criterio do eixo solo: 50% para 75%, elevando o total a 58%, aumento de 2,5 pontos percentuais. Nenhum caso de campo ou validacao agronomica foi marcado como realizado.

Campos novos sao opcionais: sampled_at, analysis_provider e report_reference. O parecer os exibe como origem declarada, com origin_verified=false. O snapshot preserva a data em JSON; o fato de pH usa essa data em vez do periodo POWER. Receber uma referencia de laudo nao comprova sua autenticidade ou representatividade espacial.

## Acompanhamento

Na bancada, usar **Consultar evolucao**. O painel lista percentuais, pesos e pendencias. No Swagger, usar GET /v1/delivery-progress. Este percentual mede criterios de conclusao, nao esforco restante: um unico criterio cientifico pode exigir mais trabalho que varios itens de interface.

Verificacao: 103 testes Python aprovados com um aviso de deprecacao existente; testes JavaScript aprovados, incluindo consulta/renderizacao do painel e envio dos campos de solo. Sem chamadas NASA reais nesta etapa.
