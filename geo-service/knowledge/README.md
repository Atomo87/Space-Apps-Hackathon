# Referências para o RAG

A pasta começa sem documentos aprovados. O serviço funciona com explicações determinísticas e informa `approved_chunks: 0` em `/v1/insights/capabilities`.

Cada arquivo JSON revisado deve seguir este formato (exemplo sintético, não usar como evidência real):

```json
{
  "id": "documento-estavel",
  "title": "Título verificado",
  "url": "https://dominio-oficial/documento",
  "region": "global",
  "crops": ["soja"],
  "version": "edicao-e-hash-revisados",
  "reviewed_at": "2026-11-15",
  "review_status": "draft",
  "chunks": [{"id": "trecho-estavel", "section": "Página e seção", "text": "Texto com unidades e contexto preservados."}]
}
```

Somente `approved` entra no índice. A aprovação é uma revisão humana, não uma conclusão do Gemini. Não incluir dados pessoais ou segredos. Trechos regionais ainda ficam fora da busca porque o contrato atual não informa a região agronômica de forma confiável. Culturas específicas são filtradas; lista vazia significa referência geral. O índice FTS5 é construído em memória a partir dos documentos aprovados. Não há upload público nem busca web automática nesta etapa.
