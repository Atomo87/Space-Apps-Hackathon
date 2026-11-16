"""RAG lexical local. Apenas trechos revisados; sem crawler ou upload publico."""
import hashlib
import json
import re
import sqlite3
from urllib.parse import urlsplit

from app.insights.contracts import Reference


class Knowledge:
    def __init__(self, directory):
        self.chunks = []
        for path in sorted(directory.glob("*.json")) if directory.exists() else []:
            document = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("Documento RAG deve ser um objeto JSON.")
            if document.get("review_status") != "approved":
                continue
            # Regiao local nao informada no contrato atual: so referencias globais.
            if document.get("region") != "global":
                continue
            if not document.get("reviewed_at") or not document.get("version"):
                raise ValueError("Referencia aprovada sem revisao ou versao.")
            if not document.get("id") or not document.get("title") or not isinstance(document.get("chunks"), list):
                raise ValueError("Documento aprovado sem identificacao ou trechos.")
            if not isinstance(document.get("crops", []), list) or any(not isinstance(c, str) for c in document.get("crops", [])):
                raise ValueError("Culturas da referencia devem ser uma lista de codigos.")
            url = urlsplit(document.get("url", ""))
            if url.scheme != "https" or not url.hostname or url.username or url.password:
                raise ValueError("Referencia deve ter URL HTTPS sem credenciais.")
            for chunk in document.get("chunks", []):
                if not isinstance(chunk, dict) or not chunk.get("id") or not chunk.get("section"):
                    raise ValueError("Trecho aprovado sem ID ou secao.")
                if not chunk.get("text") or len(chunk["text"]) > 8000:
                    raise ValueError("Trecho de referencia vazio ou muito extenso.")
                ref = Reference(id=chunk["id"], document_id=document["id"], title=document["title"],
                    url=document["url"], section=chunk["section"], version=document["version"],
                    content_hash=hashlib.sha256(chunk["text"].encode()).hexdigest(), text=chunk["text"])
                self.chunks.append((ref, document.get("crops", [])))
        ids = [ref.id for ref, _ in self.chunks]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs de referencias duplicados.")
        self.version = hashlib.sha256(json.dumps([(r.model_dump(), c) for r,c in self.chunks], sort_keys=True).encode()).hexdigest()[:16]

    def retrieve(self, query, crops):
        terms = list(dict.fromkeys(re.findall(r"[^\W_]+", query.lower())))[:16]
        if not terms or not self.chunks:
            return []
        # Indice efemero: evita dependencia vetorial; fonte persistida em JSON revisado.
        with sqlite3.connect(":memory:") as db:
            db.execute("CREATE VIRTUAL TABLE chunks USING fts5(id UNINDEXED, title, text)")
            allowed = {}
            for ref, tags in self.chunks:
                if tags and not (set(tags) & set(crops)):
                    continue
                allowed[ref.id] = ref
                db.execute("INSERT INTO chunks VALUES(?,?,?)", (ref.id, ref.title, ref.text))
            expression = " OR ".join('"'+term+'"' for term in terms)
            rows = db.execute("SELECT id FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT 4", (expression,)).fetchall()
        return [allowed[row[0]] for row in rows]
