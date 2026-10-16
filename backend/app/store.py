"""PostgreSQL repository with per-project transactional row locking."""
import re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Callable

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool


class Store:
    def __init__(self, directory: Path, database_url: str, schema: str = "public"):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", schema):
            raise ValueError("数据库 schema 名称不合法")
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.schema = schema
        self._connection = ContextVar("store_connection", default=None)
        with psycopg.connect(database_url, connect_timeout=5) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
            conn.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            conn.execute("""CREATE TABLE IF NOT EXISTS records (
                kind TEXT NOT NULL, id TEXT NOT NULL, payload JSONB NOT NULL,
                sequence BIGINT GENERATED ALWAYS AS IDENTITY,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (kind, id), CHECK (jsonb_typeof(payload) = 'object')
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS records_kind_sequence ON records (kind, sequence DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS records_book_id ON records (kind, (payload->>'book_id'))")
        self.pool = ConnectionPool(database_url, min_size=1, max_size=5, timeout=10, open=True,
                                   kwargs={"row_factory": dict_row, "options": f"-c search_path={schema}"})
        self.pool.wait(timeout=10)

    @contextmanager
    def connection(self):
        active = self._connection.get()
        if active is not None:
            # A mutation may read its source book. Reuse the transaction so it
            # cannot exhaust the pool while other writers wait on its row lock.
            with active.transaction():
                yield active
            return
        with self.pool.connection() as conn:
            token = self._connection.set(conn)
            try:
                with conn.transaction():
                    yield conn
            finally:
                self._connection.reset(token)

    def close(self):
        self.pool.close()

    def get(self, kind: str, identifier: str) -> dict:
        with self.connection() as conn:
            row = conn.execute("SELECT payload FROM records WHERE kind=%s AND id=%s", (kind, identifier)).fetchone()
        if not row:
            raise KeyError(f"找不到{kind}：{identifier}")
        return row["payload"]

    def list(self, kind: str, book_id: str | None = None) -> list[dict]:
        with self.connection() as conn:
            query = "SELECT payload FROM records WHERE kind=%s"
            values = [kind]
            if book_id is not None:
                query += " AND payload->>'book_id'=%s"
                values.append(book_id)
            rows = conn.execute(query + " ORDER BY sequence DESC", values).fetchall()
        return [row["payload"] for row in rows]

    def put(self, kind: str, value: dict) -> dict:
        with self.connection() as conn:
            conn.execute("""INSERT INTO records(kind,id,payload) VALUES(%s,%s,%s)
                ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload, updated_at=now()""",
                         (kind, value["id"], Jsonb(value)))
        return value

    def mutate(self, kind: str, identifier: str, update: Callable[[dict], None]) -> dict:
        with self.connection() as conn:
            row = conn.execute("SELECT payload FROM records WHERE kind=%s AND id=%s FOR UPDATE", (kind, identifier)).fetchone()
            if not row:
                raise KeyError(f"找不到{kind}：{identifier}")
            value = row["payload"]
            update(value)
            conn.execute("UPDATE records SET payload=%s, updated_at=now() WHERE kind=%s AND id=%s",
                         (Jsonb(value), kind, identifier))
        return value
