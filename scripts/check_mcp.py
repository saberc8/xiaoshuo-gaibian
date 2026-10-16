"""Exercise the actual stdio MCP protocol and HTTP workflow in an isolated database."""
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import uuid

import psycopg
from psycopg import sql
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.config import Settings  # noqa: E402
from backend.app.demo import demo_epub  # noqa: E402
from backend.app.epub import parse_epub  # noqa: E402


async def call(session, tool_name, **arguments):
    result = await session.call_tool(tool_name, arguments)
    if result.isError:
        raise AssertionError(f"MCP {tool_name}: {result.content}")
    if result.structuredContent:
        value = result.structuredContent
        return value["result"] if set(value) == {"result"} else value
    return json.loads(next(item.text for item in result.content if item.type == "text"))


async def check_deep_rewrite(session, http, parent_id):
    """Exercise the real MCP -> HTTP -> PostgreSQL second-draft contract."""
    parent_before = (await http.get(f'/api/adaptation-versions/{parent_id}/export?format=json')).content
    guide = await call(session, 'get_adaptation_guide', section='rewrite')
    assert {'motivation', 'conflict', 'plot_structure'} <= guide['dimensions'].keys()
    dimensions = ['motivation', 'conflict', 'plot_structure']
    project = await call(session, 'create_deep_rewrite', project_id=parent_id, name='潮汐账·深度重写协议测试', brief={
        'idea': '从个人寻找师兄转为公开举证与偿债；重组因果与人物选择。', 'target_units': 1, 'unit_characters': 100,
        'preserve': ['承担选择的代价'],
        'rewrite': {'dimensions': dimensions, 'narrative_strategy': '先写听证结果，再揭示自认责任的过程。',
                    'ending_direction': '公开自己的责任，不靠契约解决问题。', 'avoid': ['不逐句换词或照搬相同事件']}})
    assert project['status'] == 'framing' and project['chapter_ids'] == ['u1']
    assert (await http.get(f"/api/adaptations/{project['id']}/handoff")).status_code == 422
    edited = {**project['brief'], 'tone': '克制写实，突出证据与主动承担'}
    response = await http.put(f"/api/adaptations/{project['id']}/brief", json={
        'name': project['name'], 'brief': edited, 'chapter_ids': project['chapter_ids'], 'expected_revision': project['revision']})
    response.raise_for_status()
    project = response.json()
    response = await http.put(f"/api/adaptations/{project['id']}/framework", json={
        'framework': project['framework'], 'confirm': True, 'expected_revision': project['revision']})
    response.raise_for_status()
    project = response.json()
    assert 'submit_deep_rewrite_audit' in (await call(session, 'get_adaptation_handoff', project_id=project['id']))['prompt']
    evidence = []
    for stage, source in [('original', 'original'), ('baseline', 'adaptation')]:
        chunk = (await call(session, 'get_adaptation_context', project_id=project['id'], stage=stage))['items'][0]
        paragraph = chunk['paragraphs'][-1]
        evidence.append({'source': source, 'chapter_id': chunk['chapter_id'], 'paragraph_id': paragraph['id'], 'quote': paragraph['text']})
    context = await call(session, 'get_adaptation_context', project_id=project['id'])
    chunk = context['items'][0]
    project = await call(session, 'submit_source_analysis', project_id=project['id'], chunk_id=chunk['id'], expected_revision=project['revision'], analysis={
        'summary': '旧稿依赖线索与契约诱惑。', 'setting': '旧码头', 'plot_beats': ['发现契约', '暂缓交易'],
        'structural_observations': ['被动发现可改为主动交出账册，改变冲突起因。'],
        'evidence': [{'paragraph_id': evidence[1]['paragraph_id'], 'quote': evidence[1]['quote']}]})
    parent = await call(session, 'get_adaptation', project_id=parent_id)
    plan = {**parent['plan'], 'logline': '梁照主动交出账册，在听证中承担自己的责任。',
            'synopsis': '由听证结果倒推债务来源，主角为船工讨回工钱也必须偿还自己的债。',
            'units': [{'id': 'r1', 'title': '第一章·签字人', 'source_chapter_ids': ['u1'], 'objective': '公开欠款',
                       'conflict': '为船工讨回工钱会暴露自己签下的债', 'turning_point': '交出本人签名的账页',
                       'cliffhanger': '签名还能指认谁？', 'beats': ['听证判定', '回忆送账册', '认领欠款']}],
            'rewrite_design': {'diagnosis': '旧稿事件依赖外来契约，主角缺少主动制造后果的选择。',
                               'narrative_strategy': '听证结果开场，倒叙交出账册的过程。', 'ending': '承担自己的债。',
                               'retained_elements': ['选择的代价'], 'removed_elements': ['依赖契约提供线索'],
                               'changes': [{'dimension': d, 'before': '个人寻人中发现契约和脚印。',
                                            'after': '主动交出欠款证据，引发公开偿债。', 'reason': '改变行动及其后果。',
                                            'target_unit_ids': ['r1'], 'evidence': evidence} for d in dimensions]}}
    project = await call(session, 'save_adaptation_plan', project_id=project['id'], plan=plan, expected_revision=project['revision'])
    context = await call(session, 'get_adaptation_context', project_id=project['id'], stage='write', unit_id='r1')
    prose = '听证结束时，梁照的名字被写进欠款名单。前一夜他亲手把账册交给债主，要求先归还船工的工钱。债主以为他会撕掉最后一页，那里记着他的签字。他却将那页摊开，说自己当年隐瞒了沉船的实情，也该付出代价。窗外的人群安静下来。'
    project = await call(session, 'submit_adaptation_draft', project_id=project['id'], unit_id='r1', expected_revision=project['revision'], draft={
        'title': '第一章·签字人', 'paragraphs': [prose], 'summary': '梁照公开账册并承担欠款责任。',
        'continuity_notes': ['原稿契约仍存在，但本章未动用；公开证据由主角亲自提交。'],
        'change_notes': ['重设动机、冲突与倒叙组织'], 'source_chunk_ids': context['required_source_chunk_ids']})
    context = await call(session, 'get_adaptation_context', project_id=project['id'], stage='review', unit_id='r1')
    project = await call(session, 'submit_adaptation_review', project_id=project['id'], unit_id='r1', expected_revision=project['revision'], review={
        'draft_revision': 1, 'reviewed_chunk_ids': context['required_review_chunk_ids'], 'summary': '九项协议检查已提交。',
        'checks': {k: True for k in ['names', 'world_rules', 'causality', 'continuity', 'brief', 'source_traceability', 'framework_fit', 'structural_change', 'independent_expression']}, 'findings': []})
    assert project['status'] == 'auditing'
    assert (await http.post(f"/api/adaptations/{project['id']}/finalize", json={'name': project['name'], 'expected_revision': project['revision']})).status_code == 422
    context = await call(session, 'get_adaptation_context', project_id=project['id'], stage='audit')
    project = await call(session, 'submit_deep_rewrite_audit', project_id=project['id'], expected_revision=project['revision'], audit={
        'unit_revisions': context['unit_revisions'], 'reviewed_chunk_ids': context['required_review_chunk_ids'],
        'summary': '三方证据及三项结构变化已核对。', 'remaining_risks': ['协议夹具不代表文学质量评估。'],
        'comparisons': [{'dimension': d, 'unit_id': 'r1', 'paragraph_id': 'p00001', 'quote': prose,
                         'baseline': evidence, 'judgment': '主动承担自身责任触发公开偿债，改变原有事件因果。', 'passed': True} for d in dimensions]})
    assert project['status'] == 'ready'
    release = await call(session, 'finalize_adaptation', project_id=project['id'], name=project['name'], expected_revision=project['revision'])
    export = await call(session, 'get_adaptation_export_url', version_id=release['id'], format='json')
    snapshot = (await http.get(export['url'])).json()
    assert snapshot['parent_project_id'] == parent_id and snapshot['rewrite_audit']['passed']
    export = await call(session, 'get_adaptation_export_url', version_id=release['id'])
    assert len(parse_epub((await http.get(export['url'])).content, 200 * 1024 * 1024)['chapters']) == 1
    assert (await http.get(f'/api/adaptation-versions/{parent_id}/export?format=json')).content == parent_before


async def check(directory: str):
    with socket.socket() as socket_:
        socket_.bind(("127.0.0.1", 0))
        port = socket_.getsockname()[1]
    base_url = f"http://127.0.0.1:{port}"
    schema = "mcp_test_" + uuid.uuid4().hex
    database_url = Settings().database_url
    environment = {**os.environ, "NOVEL_DATA_DIR": directory, "NOVEL_API_URL": base_url,
                   "NOVEL_DATABASE_URL": database_url, "NOVEL_DATABASE_SCHEMA": schema}
    file = Path(directory) / "sample.epub"
    file.write_bytes(demo_epub())
    backend_log = (Path(directory) / "backend.log").open("w")
    backend = subprocess.Popen([sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                               cwd=ROOT, env=environment, stdout=backend_log, stderr=subprocess.STDOUT)
    try:
        async with httpx.AsyncClient(base_url=base_url) as http:
            for _ in range(100):
                try:
                    if (await http.get("/api/health")).is_success:
                        break
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(.1)
            else:
                raise RuntimeError("测试后端未能启动：" + (Path(directory) / "backend.log").read_text())
            parameters = StdioServerParameters(command=sys.executable, args=["-m", "backend.app.mcp_server"], cwd=str(ROOT), env=environment)
            async with stdio_client(parameters) as (reader, writer), ClientSession(reader, writer) as session:
                await session.initialize()
                tools = await session.list_tools()
                tool_names = {tool.name for tool in tools.tools}
                assert len(tool_names) == 22
                assert {"get_adaptation_handoff", "list_adaptations", "import_novel", "create_deep_rewrite", "submit_deep_rewrite_audit"} <= tool_names
                assert not {"import_epub", "set_character_rules", "preview_replacements", "start_codex_review", "create_version"} & tool_names
                book = await call(session, "import_novel", path=str(file))
                assert book["chapter_count"] == 8
                assert len(await call(session, "list_books")) == 1
                chapter = await call(session, "read_chapter", book_id=book["id"], chapter_id="ch0001")
                assert chapter["paragraphs"] and "characters" not in book
                health = (await http.get("/api/health")).json()
                assert health["database"] == "postgresql"
                # Structured fixtures exercise orchestration and invariants, not literary quality.
                catalog = await call(session, "get_source_catalog")
                assert len(catalog["works"]) == 10
                assert "schema" in await call(session, "get_adaptation_guide", section="plan")
                text_file = Path(directory) / "fixture.txt"
                text_file.write_text("第一回\n沈砚来到旧码头，发现了新的线索。", encoding="utf-8")
                text_book = await call(session, "import_novel", path=str(text_file))
                await call(session, "set_book_source", book_id=text_book["id"], source={"rights_basis": "own_work", "edition": "MCP 测试原文"})
                project = await call(session, "create_adaptation", book_id=text_book["id"], chapter_ids=["ch0001"], name="因果契·协议测试",
                                     brief={"idea": "把码头谜案改编为因果契约故事。", "target_units": 1, "unit_characters": 100})
                assert project["status"] == "framing"
                assert "schema" in await call(session, "get_adaptation_guide", section="framework")
                # The same HTTP routes used by the page edit the brief and lock
                # conditions; the stdio agent must then see that exact revision.
                assert (await http.get(f"/api/adaptations/{project['id']}/handoff")).status_code == 422
                edited_brief = {**project["brief"], "tone": "克制悬疑，突出选择的代价"}
                response = await http.put(f"/api/adaptations/{project['id']}/brief", json={
                    "name": project["name"], "brief": edited_brief, "chapter_ids": project["chapter_ids"],
                    "expected_revision": project["revision"]})
                response.raise_for_status()
                project = response.json()
                framework = {"era": "架空临海旧城", "time_span": "本次故事三日内", "locations": ["旧码头"],
                             "historical_policy": "人物与事件虚构，不对应真实史案。", "naming_policy": "统一中文姓名。",
                             "plot_spine": ["发现线索与契约", "面对有代价的选择"], "prohibited_elements": ["不临时增加无限能力"],
                             "forbidden_terms": ["二维码"], "scope_note": "本次仅改写一章测试原文。"}
                response = await http.put(f"/api/adaptations/{project['id']}/framework", json={
                    "framework": framework, "confirm": True, "expected_revision": project["revision"]})
                response.raise_for_status()
                project = response.json()
                handoff = await call(session, "get_adaptation_handoff", project_id=project["id"])
                assert handoff["revision"] == project["revision"] and project["id"] in handoff["prompt"]
                assert (await call(session, "get_adaptation", project_id=project["id"]))["brief"] == edited_brief
                assert len(await call(session, "list_adaptations")) == 1
                context = await call(session, "get_adaptation_context", project_id=project["id"])
                chunk = context["items"][0]
                paragraph = chunk["paragraphs"][-1]
                project = await call(session, "submit_source_analysis", project_id=project["id"], chunk_id=chunk["id"], expected_revision=project["revision"],
                                     analysis={"summary": "沈砚在码头发现线索。", "setting": "旧码头", "characters": [{"name": "沈砚", "role": "探案者"}],
                                               "plot_beats": ["抵达码头", "发现线索"], "evidence": [{"paragraph_id": paragraph["id"], "quote": paragraph["text"]}]})
                plan = {"logline": "探案者在码头找到一枚用记忆兑换答案的契约。", "synopsis": "主角面对交易诱惑，选择先用自己的观察追查真相。",
                        "bible": {"setting": "临海旧城", "tone": "克制悬疑", "naming_strategy": "中文姓名与称谓保持一致",
                                  "characters": [{"id": "liang", "source_names": ["沈砚"], "target_name": "梁照", "role": "探案者", "motivation": "找出失踪的师兄", "arc": "从依赖捷径到承担选择"}],
                                  "world_rules": [{"id": "memory", "rule": "契约可用记忆兑换答案", "cost": "失去一段关系记忆", "limit": "最多三次"}], "immutable_facts": ["支付的记忆不能恢复"]},
                        "units": [{"id": "u1", "title": "第一章·潮痕", "source_chapter_ids": ["ch0001"], "objective": "寻找师兄", "conflict": "答案需要记忆", "turning_point": "发现能力代价", "cliffhanger": "线索指向谁？", "beats": ["抵达码头", "发现契约", "暂缓交易"]}]}
                project = await call(session, "save_adaptation_plan", project_id=project["id"], plan=plan, expected_revision=project["revision"])
                context = await call(session, "get_adaptation_context", project_id=project["id"], stage="write", unit_id="u1")
                draft = {"title": "第一章·潮痕", "paragraphs": ["梁照沿潮痕走进旧码头，在系船柱下发现一枚残缺的契约。师兄留下的字迹告诉他，答案需要用记忆交换，支付之后不能恢复。他想起临行前的告诫，把契约收回袖中，转而俯身查看木板上尚未干透的脚印。"],
                         "summary": "梁照发现契约，选择先追查脚印。", "continuity_notes": ["契约尚未使用", "记忆不可恢复"], "change_notes": ["增加因果契约和选择代价"], "source_chunk_ids": context["required_source_chunk_ids"]}
                project = await call(session, "submit_adaptation_draft", project_id=project["id"], unit_id="u1", draft=draft, expected_revision=project["revision"])
                assert (await call(session, "read_adaptation_unit", project_id=project["id"], unit_id="u1"))["draft"]["paragraphs"] == draft["paragraphs"]
                context = await call(session, "get_adaptation_context", project_id=project["id"], stage="review", unit_id="u1")
                project = await call(session, "submit_adaptation_review", project_id=project["id"], unit_id="u1", expected_revision=project["revision"],
                                     review={"draft_revision": 1, "reviewed_chunk_ids": context["required_review_chunk_ids"], "summary": "协议测试检查通过。",
                                             "checks": {key: True for key in ("names", "world_rules", "causality", "continuity", "brief", "source_traceability", "framework_fit")}, "findings": []})
                release = await call(session, "finalize_adaptation", project_id=project["id"], name="因果契·协议测试", expected_revision=project["revision"])
                assert (await call(session, "get_adaptation", project_id=project["id"]))["status"] == "completed"
                assert len(await call(session, "list_adaptations", book_id=text_book["id"])) == 1
                export = await call(session, "get_adaptation_export_url", version_id=release["id"])
                rewritten = await http.get(export["url"])
                rewritten.raise_for_status()
                assert parse_epub(rewritten.content, 200 * 1024 * 1024)["title"] == "因果契·协议测试"
                await check_deep_rewrite(session, http, release['id'])
                print(json.dumps({"status": "passed", "mcp_tools": len(tools.tools), "database": "PostgreSQL",
                                  "selected_chapters": 1, "epub_roundtrip": "passed", "removed_rename_tools": "absent",
                                  "deep_rewrite": "immutable parent → page-edited conditions → structural diagnosis → dual-source plan → draft → nine checks → global three-way audit → immutable EPUB/JSON",
                                  "adaptation": "TXT → page-edited conditions → locked framework → MCP handoff → evidence → bible/outline → draft → seven-check review → immutable EPUB"}, ensure_ascii=False))
    finally:
        backend.terminate()
        try:
            backend.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend.kill()
            backend.wait(timeout=5)
        backend_log.close()
        with psycopg.connect(database_url) as conn:
            conn.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="xuzhang-mcp-") as directory:
        asyncio.run(check(directory))
