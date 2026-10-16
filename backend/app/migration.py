"""One-way, non-destructive SQLite → PostgreSQL migration for existing workspaces."""
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from psycopg.types.json import Jsonb
from .store import Store


def migrate_sqlite(source: Path, store: Store, backup_dir: Path) -> dict:
    if not source.is_file():
        raise ValueError(f"SQLite 源文件不存在：{source}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    snapshot = backup_dir / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-studio.sqlite3')
    with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(snapshot) as backup:
            original.backup(backup)
            rows = backup.execute('SELECT kind,id,payload FROM records ORDER BY rowid').fetchall()
    records = [(kind, identifier, json.loads(payload)) for kind, identifier, payload in rows]
    inserted = 0
    with store.connection() as conn:
        for kind, identifier, payload in records:
            if payload.get('id') != identifier:
                raise ValueError(f"源记录标识不一致：{kind}/{identifier}")
            existing = conn.execute('SELECT payload FROM records WHERE kind=%s AND id=%s FOR UPDATE', (kind, identifier)).fetchone()
            if existing and existing['payload'] != payload:
                raise ValueError(f"目标已有不同内容，迁移已回滚：{kind}/{identifier}")
            if not existing:
                conn.execute('INSERT INTO records(kind,id,payload) VALUES(%s,%s,%s)', (kind, identifier, Jsonb(payload)))
                inserted += 1
        for kind, identifier, payload in records:
            actual = conn.execute('SELECT payload FROM records WHERE kind=%s AND id=%s', (kind, identifier)).fetchone()
            if actual['payload'] != payload:
                raise ValueError(f"迁移校验失败：{kind}/{identifier}")
    return {'records': len(records), 'inserted': inserted, 'verified': len(records),
            'by_kind': dict(Counter(kind for kind, _, _ in records)), 'backup': str(snapshot), 'original_files': 'unchanged'}
