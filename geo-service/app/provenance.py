"""Recibos locais: vincular exatamente o perfil servido ao ponto consultado.

Nao e assinatura NASA. Confia no cliente de origem e no cache local do servidor.
"""
import hashlib
import json
import time
from uuid import uuid4
from app.insights.store import SnapshotStore, encode


def digest(payload):
    def normalize(value):
        # JSON.stringify no navegador converte 1.0 para 1; isso nao e adulteracao.
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, dict):
            return {str(k): normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        return value
    content = normalize({k: v for k, v in payload.items() if k != '_receipt'})
    return hashlib.sha256(encode(content).encode()).hexdigest()


def store_for(cfg):
    store = SnapshotStore(cfg.cache_dir, cfg.insights_snapshot_ttl_hours)
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS source_receipts(id TEXT PRIMARY KEY, expires REAL, kind TEXT, lat REAL, lon REAL, hash TEXT)')
        db.execute('DELETE FROM source_receipts WHERE expires<=?', (time.time(),))
    return store


def register(payload, kind, latitude, longitude, cfg):
    store = store_for(cfg)
    identifier = str(uuid4())
    fingerprint = digest(payload)
    expiry = time.time() + store.ttl
    with store.connect() as db:
        db.execute('INSERT INTO source_receipts VALUES(?,?,?,?,?,?)',
                   (identifier, expiry, kind, latitude, longitude, fingerprint))
        db.execute('DELETE FROM source_receipts WHERE id IN (SELECT id FROM source_receipts ORDER BY expires DESC LIMIT -1 OFFSET 2000)')
    return {**payload, '_receipt': {'id': identifier, 'sha256': fingerprint, 'expires_unix': expiry}}


def verify(req, cfg):
    statuses = {}
    store = store_for(cfg)
    for kind in ('climate', 'terrain', 'vegetation', 'stress', 'earthdata'):
        profile = getattr(req, kind)
        if profile is None:
            continue
        receipt = profile.get('_receipt')
        identifier = receipt.get('id') if isinstance(receipt, dict) else None
        with store.connect() as db:
            row = db.execute('SELECT expires,kind,lat,lon,hash FROM source_receipts WHERE id=?', (identifier,)).fetchone()
        valid = bool(row and row[0] > time.time() and row[1] == kind
                     and abs(row[2] - req.field.latitude) < 1e-6
                     and abs(row[3] - req.field.longitude) < 1e-6 and row[4] == digest(profile))
        if not valid and cfg.require_verified_profiles:
            raise ValueError('Perfil ' + kind + ' sem recibo valido, alterado, expirado ou de outro local. Consulte novamente a fonte neste servidor.')
        statuses[kind] = 'server_receipt_verified' if valid else 'unverified'
    return {'profiles': statuses, 'meaning': 'Integridade e ponto conferidos contra consulta registrada no servidor; nao e assinatura NASA ou validacao agronomica.'}
