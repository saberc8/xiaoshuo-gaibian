"""Deep-rewrite state transitions, structural coverage, evidence and frozen lineage."""
import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.adaptation import adaptation_guide
from backend.app.adaptation_models import RewriteRequirements
from backend.app.epub import parse_epub
from backend.app.main import create_app
from test_adaptation import (workspace, create_project, analyze_all, make_plan,
                             write_all, review_all, draft_for, review_for)


DIMENSIONS = ['motivation', 'conflict', 'plot_structure']


def rewrite_request(units=1):
    return {'name': '潮汐账 · 深度重写', 'brief': {
        'idea': '从私人许愿转为公开举证，重新组织人物选择、利益冲突和因果。',
        'target_units': units, 'unit_characters': 100,
        'preserve': ['核心情感与选择的代价'],
        'rewrite': {'dimensions': DIMENSIONS, 'narrative_strategy': '先写结果，再由双方证言重组原因。',
                    'ending_direction': '主角公开自己的责任。', 'avoid': ['不逐章换词和改名']}}}


@pytest.fixture
def completed(workspace):
    _, _, service = workspace
    project = analyze_all(service, create_project(workspace))
    project = service.save_plan(project['id'], make_plan(), project['revision'])
    project = review_all(service, write_all(service, project))
    service.finalize(project['id'], project['name'], project['revision'])
    return service, service.get(project['id'])


def diagnose(service, project):
    project = service.save_framework(project['id'], project['framework'], True, project['revision'])
    cursor = 0
    while cursor is not None:
        context = service.context(project['id'], 'analysis', cursor, 3)
        for chunk in context['items']:
            paragraph = chunk['paragraphs'][-1]
            project = service.submit_analysis(project['id'], chunk['id'], {
                'summary': '主角暂缓许愿，并寻找答案。', 'setting': '临海旧城', 'plot_beats': ['发现命牌', '暂缓交易'],
                'structural_observations': ['主角被动接收规则，可改为主动公开证据并承担代价。'],
                'evidence': [{'paragraph_id': paragraph['id'], 'quote': paragraph['text']}],
            }, project['revision'])
        cursor = context['next_cursor']
    return project


def evidence_for(service, project):
    evidence = []
    for stage, source in [('original', 'original'), ('baseline', 'adaptation')]:
        chunk = service.context(project['id'], stage)['items'][0]
        paragraph = chunk['paragraphs'][-1]
        evidence.append({'source': source, 'chapter_id': chunk['chapter_id'],
                         'paragraph_id': paragraph['id'], 'quote': paragraph['text']})
    return evidence


def reconstruction(service, project):
    plan = make_plan(1)
    plan['units'] = [{**plan['units'][0], 'id': f'r{i}', 'title': f'重写第{i}章',
                      'source_chapter_ids': project['chapter_ids']}
                     for i in range(1, project['brief']['target_units'] + 1)]
    plan['rewrite_design'] = {
        'diagnosis': '旧稿逐章保留相同的交易诱惑，人物主动选择不足。',
        'narrative_strategy': '合并原章，先公开听证，再揭示债务来源。', 'ending': '主动公开自身责任。',
        'retained_elements': ['承担选择代价'], 'removed_elements': ['逐次许愿的相同循环'],
        'changes': [{'dimension': dimension, 'before': f'原稿的 {dimension} 围绕个人交易。',
                     'after': f'新稿的 {dimension} 围绕公开证据与集体偿债。',
                     'reason': '改变人物行动造成的后果，而不只改动名词。',
                     'target_unit_ids': [u['id'] for u in plan['units']],
                     'evidence': evidence_for(service, project)} for dimension in DIMENSIONS],
    }
    return plan


def rewrite_all(service, project):
    for unit in project['units']:
        draft = draft_for(service, project, unit['id'])
        draft.update(paragraphs=['听证前夜，林照将账册送到债主手中，承认当年的签字出自自己。他要救的并非师兄，而是被自己的谎言拖下水的船工。账册公开后，债主必须交出船只，工钱才能归还。林照把最后一页留在桌上，那里还记着自己的欠款。'],
                     summary='林照主动公开欠款，发起听证。', change_notes=['由私人许愿改为公开偿债与证据冲突'])
        project = service.submit_draft(project['id'], unit['id'], draft, project['revision'])
    return project


def review_rewrites(service, project):
    for unit in project['units']:
        review = review_for(service, project, unit['id'])
        review['checks'].update(structural_change=True, independent_expression=True)
        project = service.submit_review(project['id'], unit['id'], review, project['revision'])
    return project


def audit_for(service, project):
    context = service.context(project['id'], 'audit', limit=3)
    comparisons = []
    for change in project['plan']['rewrite_design']['changes']:
        for unit_id in change['target_unit_ids']:
            draft = service.read_unit(project['id'], unit_id)['draft']
            comparisons.append({'dimension': change['dimension'], 'unit_id': unit_id, 'paragraph_id': 'p00001',
                                'quote': draft['paragraphs'][0], 'baseline': evidence_for(service, project),
                                'judgment': '主动公开责任引发集体偿债，事件因果与原有许愿诱惑不同。', 'passed': True})
    return {'unit_revisions': context['unit_revisions'], 'reviewed_chunk_ids': context['required_review_chunk_ids'],
            'summary': '逐项核对结构变化，证据覆盖全部重写章。', 'comparisons': comparisons,
            'remaining_risks': ['测试夹具只验证工作流，不证明文学效果。']}


def ready_for_audit(service, parent, units=1):
    project = diagnose(service, service.create_rewrite(parent['id'], rewrite_request(units)))
    project = service.save_plan(project['id'], reconstruction(service, project), project['revision'])
    return review_rewrites(service, rewrite_all(service, project))


def test_deep_rewrite_requires_completed_parent_and_structural_conditions(workspace, completed):
    service, parent = completed
    pending = create_project(workspace)
    with pytest.raises(ValueError, match='保存独立版本'):
        service.create_rewrite(pending['id'], rewrite_request())
    invalid = deepcopy(rewrite_request())
    invalid['brief'].pop('rewrite')
    with pytest.raises(ValidationError, match='结构要求'):
        service.create_rewrite(parent['id'], invalid)
    for dimensions in [['conflict', 'motivation', 'voice'], ['motivation', 'theme', 'pov'], ['conflict'] * 3]:
        with pytest.raises(ValidationError):
            RewriteRequirements.model_validate({**rewrite_request()['brief']['rewrite'], 'dimensions': dimensions})
    with pytest.raises(ValueError, match='已完成版本'):
        service.create(parent['book_id'], {**rewrite_request(), 'chapter_ids': parent['chapter_ids']})


def test_deep_rewrite_page_edit_scope_lock_and_source_views(completed, tmp_path):
    service, parent = completed
    before = service.export(parent['id'], 'json')[0]
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(f"/api/adaptations/{parent['id']}/deep-rewrites", json=rewrite_request())
        assert response.status_code == 201
        project = response.json()
        assert project['mode'] == 'deep_rewrite' and project['chapter_ids'] == ['u1', 'u2']
        assert project['status'] == 'framing' and project['framework']['characters'] == []
        assert project['original_chapter_ids'] == ['ch0001', 'ch0002']
        assert client.get(f"/api/adaptations/{project['id']}/handoff").status_code == 422
        assert client.get(f"/api/adaptations/{project['id']}/source-chapters/u1").json()['paragraphs']
        assert client.get(f"/api/adaptations/{project['id']}/source-chapters/ch0001").status_code == 404
        edit = {'name': project['name'], 'brief': project['brief'], 'chapter_ids': ['u1'], 'expected_revision': 0}
        assert client.put(f"/api/adaptations/{project['id']}/brief", json=edit).status_code == 422
        edit['chapter_ids'] = project['chapter_ids']
        edit['brief']['rewrite']['ending_direction'] = '公开签字人的责任，不以死亡逃避。'
        project = client.put(f"/api/adaptations/{project['id']}/brief", json=edit).json()
        assert project['revision'] == 1 and not project['framework_confirmed']
        project = service.save_framework(project['id'], project['framework'], True, project['revision'])
        handoff = client.get(f"/api/adaptations/{project['id']}/handoff").json()
        assert 'submit_deep_rewrite_audit' in handoff['prompt']
        assert 'original' in handoff['prompt'] and handoff['revision'] == project['revision']
    assert service.export(parent['id'], 'json')[0] == before


def test_deep_rewrite_requires_diagnosis_design_and_real_dual_source_evidence(completed):
    service, parent = completed
    project = service.create_rewrite(parent['id'], rewrite_request())
    with pytest.raises(ValueError, match='锁定'):
        analyze_all(service, project)
    project = service.save_framework(project['id'], project['framework'], True, project['revision'])
    with pytest.raises(ValueError, match='structural_observations'):
        analyze_all(service, project)
    project = diagnose(service, project)
    assert project['completed_chunks'] == project['total_chunks'] == 2
    with pytest.raises(ValueError, match='重构方案'):
        service.save_plan(project['id'], make_plan(1), project['revision'])
    plan = reconstruction(service, project)
    bad = deepcopy(plan)
    bad['rewrite_design']['changes'][0]['evidence'][0]['quote'] = '伪造的原著证据'
    with pytest.raises(ValueError, match='逐字'):
        service.save_plan(project['id'], bad, project['revision'])
    bad = deepcopy(plan)
    bad['rewrite_design']['changes'][0]['evidence'][0] = bad['rewrite_design']['changes'][0]['evidence'][1]
    with pytest.raises(ValueError, match='同时引用'):
        service.save_plan(project['id'], bad, project['revision'])
    bad = deepcopy(plan)
    bad['rewrite_design']['changes'][0]['target_unit_ids'] = ['missing']
    with pytest.raises(ValueError, match='不存在'):
        service.save_plan(project['id'], bad, project['revision'])
    project = service.save_plan(project['id'], plan, project['revision'])
    assert len(project['units']) == 1  # two parent chapters merge into one, no 1:1 constraint


def test_deep_rewrite_rejects_unchanged_prose_and_missing_extended_checks(completed):
    service, parent = completed
    project = diagnose(service, service.create_rewrite(parent['id'], rewrite_request()))
    project = service.save_plan(project['id'], reconstruction(service, project), project['revision'])
    draft = draft_for(service, project, 'r1')
    draft['paragraphs'] = service.read_unit(parent['id'], 'u1')['draft']['paragraphs']
    with pytest.raises(ValueError, match='原样'):
        service.submit_draft(project['id'], 'r1', draft, project['revision'])
    project = rewrite_all(service, project)
    with pytest.raises(ValueError, match='structural_change'):
        service.submit_review(project['id'], 'r1', review_for(service, project, 'r1'), project['revision'])
    project = review_rewrites(service, project)
    assert project['status'] == 'auditing'
    assert project['next_action']['tool'] == 'submit_deep_rewrite_audit'
    with pytest.raises(ValueError, match='完整 Agent 审查'):
        service.finalize(project['id'], project['name'], project['revision'])


def test_global_audit_cannot_skip_revisions_chunks_pairs_or_fake_quotes(completed):
    service, parent = completed
    project = ready_for_audit(service, parent, units=2)
    audit = audit_for(service, project)
    mutations = [
        ('修订已过期', lambda a: a['unit_revisions'].update(r1=0)),
        ('全部当前稿件分块', lambda a: a['reviewed_chunk_ids'].pop()),
        ('每个维度及其全部目标章节', lambda a: a['comparisons'].pop()),
        ('指定段落', lambda a: a['comparisons'][0].update(quote='并不存在的重写证据')),
        ('逐字', lambda a: a['comparisons'][0]['baseline'][0].update(quote='虚构原著证据')),
    ]
    for message, change in mutations:
        bad = deepcopy(audit)
        change(bad)
        with pytest.raises(ValueError, match=message):
            service.submit_rewrite_audit(project['id'], bad, project['revision'])
    with pytest.raises(ValueError, match='revision='):
        service.submit_rewrite_audit(project['id'], audit, 0)
    audit['comparisons'][0]['passed'] = False
    project = service.submit_rewrite_audit(project['id'], audit, project['revision'])
    assert project['status'] == 'auditing' and not project['rewrite_audit']['passed']
    with pytest.raises(ValueError):
        service.finalize(project['id'], project['name'], project['revision'])


def test_audit_invalidation_frozen_lineage_and_recursive_rewrite(completed):
    service, parent = completed
    before = service.export(parent['id'], 'json')[0]
    project = ready_for_audit(service, parent)
    audit = audit_for(service, project)
    project = service.submit_rewrite_audit(project['id'], audit, project['revision'])
    assert project['status'] == 'ready'
    assert service.submit_rewrite_audit(project['id'], audit, 0)['revision'] == project['revision']
    draft = service.read_unit(project['id'], 'r1')['draft']
    draft['paragraphs'][0] += '他的笔尖没有再停下。'
    project = service.submit_draft(project['id'], 'r1', draft, project['revision'])
    assert project['rewrite_audit'] is None and project['status'] == 'reviewing'
    project = review_rewrites(service, project)
    with pytest.raises(ValueError, match='修订已过期'):
        service.submit_rewrite_audit(project['id'], audit, project['revision'])
    project = service.submit_rewrite_audit(project['id'], audit_for(service, project), project['revision'])
    release = service.finalize(project['id'], project['name'], project['revision'])
    snapshot = json.loads(service.export(release['id'], 'json')[0])
    assert snapshot['rewrite_audit']['passed'] and snapshot['parent_project_id'] == parent['id']
    assert snapshot['original_chapter_ids'] == parent['chapter_ids']
    assert snapshot['plan']['rewrite_design'] and snapshot['parent_release_sha256']
    assert len(parse_epub(service.export(release['id'], 'epub')[0], 200 * 1024 * 1024)['chapters']) == 1
    assert service.export(parent['id'], 'json')[0] == before
    child = service.create_rewrite(project['id'], rewrite_request())
    assert child['parent_project_id'] == project['id'] and child['original_chapter_ids'] == parent['chapter_ids']
    assert service.context(child['id'], 'original')['items'][0]['chapter_id'] == 'ch0001'
    assert service.context(child['id'], 'baseline')['items'][0]['chapter_id'] == 'r1'


def test_deep_rewrite_schema_discovery():
    assert len(adaptation_guide('rewrite')['dimensions']) == 8
    for name in ['rewrite_requirements', 'rewrite_design', 'rewrite_audit']:
        assert 'schema' in adaptation_guide(name)
