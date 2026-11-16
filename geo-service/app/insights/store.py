"""Snapshots locais: TTL, tamanho limitado, IDs imprevisiveis e cache de insights.

O token autentica o servico. Em producao o Laravel deve validar a propriedade
da analise; este armazenamento nao implementa contas de produtores.
"""
import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))


class SnapshotStore:
    def __init__(self, directory, ttl_hours=24):
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "insights.sqlite3"
        self.ttl = max(1, ttl_hours) * 3600
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS snapshots(id TEXT PRIMARY KEY, expires REAL, payload TEXT);
                CREATE TABLE IF NOT EXISTS insight_cache(key TEXT PRIMARY KEY, snapshot_id TEXT REFERENCES snapshots(id) ON DELETE CASCADE, payload TEXT);
                CREATE TABLE IF NOT EXISTS generation_budget(day TEXT PRIMARY KEY, used INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS generation_attempts(snapshot_id TEXT PRIMARY KEY REFERENCES snapshots(id) ON DELETE CASCADE);
            """)
            db.execute("DELETE FROM snapshots WHERE expires <= ?", (time.time(),))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, result, inputs):
        now = time.time()
        identifier = str(uuid4())
        raw = {"result": result, "inputs": inputs}
        digest = hashlib.sha256(encode(raw).encode()).hexdigest()
        result = dict(result, analysis_id=identifier,
                      created_at=datetime.fromtimestamp(now, timezone.utc).isoformat(),
                      expires_at=datetime.fromtimestamp(now+self.ttl, timezone.utc).isoformat())
        payload = {"result": result, "inputs": inputs, "snapshot_hash": digest}
        with self.connect() as db:
            db.execute("INSERT INTO snapshots VALUES(?,?,?)", (identifier, now+self.ttl, encode(payload)))
            # Retencao limitada para a bancada; nao e um arquivo permanente de analises.
            db.execute("DELETE FROM snapshots WHERE id IN (SELECT id FROM snapshots ORDER BY expires DESC LIMIT -1 OFFSET 1000)")
        return result

    def get(self, identifier):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM snapshots WHERE id=? AND expires>?", (str(identifier), time.time())).fetchone()
        return json.loads(row[0]) if row else None

    def cached(self, key):
        with self.connect() as db:
            row = db.execute("SELECT payload FROM insight_cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, key, identifier, response):
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO insight_cache VALUES(?,?,?)", (key, str(identifier), encode(response)))

    def claim_generation(self, identifier):
        # Uma tentativa Gemini por snapshot, inclusive timeout/erro. Sem retry oculto.
        with self.connect() as db:
            # Transacao serializada: novos snapshots nao contornam o teto global.
            db.execute("BEGIN IMMEDIATE")
            day = datetime.now(timezone.utc).date().isoformat()
            db.execute("DELETE FROM generation_budget WHERE day <> ?", (day,))
            used = db.execute("SELECT used FROM generation_budget WHERE day=?", (day,)).fetchone()
            if used and used[0] >= 20:
                return False
            claimed = db.execute("INSERT OR IGNORE INTO generation_attempts VALUES(?)", (str(identifier),)).rowcount == 1
            if claimed:
                db.execute("INSERT INTO generation_budget VALUES(?,1) ON CONFLICT(day) DO UPDATE SET used=used+1", (day,))
            return claimed
