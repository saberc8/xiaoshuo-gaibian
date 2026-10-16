import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from backend.app.migration import migrate_sqlite
from backend.app.service import Studio
from backend.app.config import Settings
from test_adaptation import workspace, create_project, analyze_all, make_plan, republic_framework


def test_all_projects_filters_and_conditions_handoff(workspace):
    _, book, adaptations = workspace
    project = create_project(workspace, lock_framework=False)
    assert project['status'] == 'framing'
    with pytest.raises(ValueError, match='锁定'):
        adaptations.handoff(project['id'])
    assert [p['id'] for p in adaptations.list()] == [project['id']]
    assert adaptations.list(book['id'])[0]['id'] == project['id']
    project = adaptations.save_framework(project['id'], republic_framework(), True, project['revision'])
    handoff = adaptations.handoff(project['id'])
    assert str(project['revision']) in handoff['prompt']
    assert project['id'] in handoff['prompt'] and '不得自行更改约定' in handoff['prompt']
    assert handoff['framework_revision'] == project['framework_revision']


def test_editing_requirements_invalidates_analysis_and_requires_relocking(workspace):
    _, _, adaptations = workspace
    project = analyze_all(adaptations, create_project(workspace))
    before = project['revision']
    changed = {**project['brief'], 'idea': '以民国港口为背景，重构冤案与归来。', 'target_units': 1}
    with pytest.raises(ValueError, match='revision'):
        adaptations.update_brief(project['id'], '新方向', changed, ['ch0001'], before-1)
    project = adaptations.update_brief(project['id'], '新方向', changed, ['ch0001'], before)
    assert project['completed_chunks'] == 0 and project['status'] == 'framing'
    assert not project['framework_confirmed'] and project['total_chunks'] == 1
    assert project['brief']['target_units'] == 1 and project['name'] == '新方向'
    with pytest.raises(ValueError, match='锁定'):
        adaptations.handoff(project['id'])
    project = adaptations.save_framework(project['id'], project['framework'], True, project['revision'])
    assert adaptations.handoff(project['id'])['revision'] == project['revision']


def test_frozen_conditions_and_duplicate_project_are_independent(workspace):
    _, book, adaptations = workspace
    project = analyze_all(adaptations, create_project(workspace))
    project = adaptations.save_plan(project['id'], make_plan(), project['revision'])
    with pytest.raises(ValueError, match='已冻结'):
        adaptations.update_brief(project['id'], '改名', project['brief'], project['chapter_ids'], project['revision'])
    copy = adaptations.create(book['id'], {'name': '另一个方案', 'brief': project['brief'], 'chapter_ids': project['chapter_ids'], 'framework': project['framework']})
    assert copy['id'] != project['id'] and copy['status'] == 'framing'
    assert not copy['framework_confirmed'] and not copy['plan'] and not copy['units']
    assert adaptations.get(project['id']) == project


def test_postgres_concurrent_mutations_and_rollback(workspace):
    studio, _, _ = workspace
    store = studio.store
    store.put('counter', {'id': 'one', 'n': 0})
    store.pool.resize(1, 1)
    def increment(_):
        def update(value):
            assert store.get('counter', 'one')['n'] == value['n']
            value['n'] += 1
        store.mutate('counter', 'one', update)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(increment, range(40)))
    assert store.get('counter','one')['n'] == 40
    def fail(value):
        value['n'] = 999
        raise ValueError('rollback')
    with pytest.raises(ValueError):
        store.mutate('counter','one',fail)
    assert store.get('counter','one')['n'] == 40
    reopened = Studio(studio.settings)
    assert reopened.store.get('counter','one')['n'] == 40


def test_sqlite_migration_backup_exact_replay_and_conflict_rollback(workspace, tmp_path):
    studio, _, _ = workspace
    source = tmp_path / 'legacy.sqlite3'
    payloads = [('book', 'legacy-book', {'id':'legacy-book','title':'旧原著'}), ('adaptation','legacy-project', {'id':'legacy-project','framework':{'era':'民国'},'_release':{'text':'不可丢失的正文'}})]
    with sqlite3.connect(source) as conn:
        conn.execute('CREATE TABLE records(kind TEXT,id TEXT,payload TEXT)')
        conn.executemany('INSERT INTO records VALUES(?,?,?)',[(k,i,json.dumps(p,ensure_ascii=False)) for k,i,p in payloads])
    report = migrate_sqlite(source, studio.store, tmp_path/'backups')
    assert report['inserted'] == report['verified'] == 2 and Path(report['backup']).is_file()
    for kind, identifier, payload in payloads:
        assert studio.store.get(kind, identifier) == payload
    assert migrate_sqlite(source, studio.store, tmp_path/'backups')['inserted'] == 0
    studio.store.mutate('adaptation','legacy-project',lambda p: p.update(name='更新后的项目'))
    with sqlite3.connect(source) as conn:
        conn.execute('INSERT INTO records(rowid,kind,id,payload) VALUES(0,?,?,?)',('book','new-before-conflict','{"id":"new-before-conflict"}'))
    with pytest.raises(ValueError, match='回滚'):
        migrate_sqlite(source, studio.store, tmp_path/'backups')
    with pytest.raises(KeyError):
        studio.store.get('book','new-before-conflict')
    assert studio.store.get('adaptation','legacy-project')['name'] == '更新后的项目'


def test_http_project_workflow_and_removed_rename_surface(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        assert client.get('/api/health').json()['database'] == 'postgresql'
        book = client.post('/api/books',files={'file':('试样.txt','第一章\n归航。'.encode())}).json()
        base = {'name':'页面编辑方案','chapter_ids':['ch0001'],'brief':{'idea':'民国本土化','target_units':1}}
        project = client.post(f'/api/books/{book["id"]}/adaptations',json=base).json()
        assert project['status'] == 'framing'
        assert client.get('/api/adaptations').json()[0]['id'] == project['id']
        assert client.get(f'/api/adaptations/{project["id"]}/handoff').status_code == 422
        assert client.post(f'/api/books/{book["id"]}/adaptations',json={**base,'require_framework':False}).status_code == 422
        updated = client.put(f'/api/adaptations/{project["id"]}/brief',json={**base,'name':'修改后的名称','expected_revision':project['revision']})
        assert updated.status_code == 200 and updated.json()['name'] == '修改后的名称'
        paths = client.get('/openapi.json').json()['paths']
        assert not any('/characters' in p or '/reviews' in p or '/preview' in p or p.startswith('/api/versions') for p in paths)
        assert 'characters' not in book
        assert 'llm' not in client.get('/api/system').json()
