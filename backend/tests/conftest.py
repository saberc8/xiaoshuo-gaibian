"""Every test gets a private PostgreSQL schema; production rows are never touched."""
import os
import uuid
import pytest
import psycopg
from psycopg import sql
from backend.app.config import Settings
from backend.app.store import Store

DATABASE_URL = Settings().database_url
SESSION_SCHEMA = 'test_session_' + uuid.uuid4().hex
os.environ['NOVEL_DATABASE_SCHEMA'] = SESSION_SCHEMA


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    schema = 'test_' + uuid.uuid4().hex
    monkeypatch.setenv('NOVEL_DATABASE_SCHEMA', schema)
    monkeypatch.setenv('NOVEL_DATABASE_URL', DATABASE_URL)
    stores = []
    initialize = Store.__init__
    def tracked(self, *args, **kwargs):
        initialize(self, *args, **kwargs)
        stores.append(self)
    monkeypatch.setattr(Store, '__init__', tracked)
    yield
    for store in stores:
        store.close()
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(schema)))


def pytest_sessionfinish(session, exitstatus):
    from backend.app.main import app
    app.state.studio.store.close()
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(sql.SQL('DROP SCHEMA IF EXISTS {} CASCADE').format(sql.Identifier(SESSION_SCHEMA)))
