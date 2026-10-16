import hashlib
import json
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from backend.app.adaptation import Adaptations, adaptation_guide
from backend.app.config import Settings
from backend.app.epub import parse_epub
from backend.app.main import create_app
from backend.app.service import Studio


@pytest.fixture
def workspace(tmp_path):
    studio = Studio(Settings(data_dir=tmp_path, _env_file=None))
    book = studio.import_book("Chapter I\nHenry Jekyll made a dangerous wish.\n\nChapter II\nEdward Hyde paid its price.".encode(), "Dual Life.txt")
    return studio, book, Adaptations(studio)


def create_project(workspace, units=2, preset="custom", lock_framework=True, **brief):
    _, book, adaptations = workspace
    project = adaptations.create(book["id"], {"name": "心魔契", "chapter_ids": ["ch0001", "ch0002"],
                                          "brief": {"idea": "将双重身份改成心魔交易，统一中文人物名。", "preset": preset,
                                                    "target_units": units, "unit_characters": 100, **brief}})
    if lock_framework:
        framework = {**republic_framework(), 'characters': [], 'era': '架空世界', 'time_span': '三日内'}
        project = adaptations.save_framework(project['id'], framework, True, project['revision'])
    return project


def analyze_all(adaptations, project):
    context = adaptations.context(project["id"], "analysis", cursor=0, limit=3)
    for chunk in context["items"]:
        paragraph = chunk["paragraphs"][-1]
        analysis = {"summary": "角色许愿并面对代价。", "characters": [{"name": "Henry Jekyll", "aliases": ["Jekyll"], "role": "做出危险选择的主角"}],
                    "setting": "秘密实验中的双重身份。", "plot_beats": ["许愿", "付出代价"], "opportunities": ["心魔契约"],
                    "evidence": [{"paragraph_id": paragraph["id"], "quote": paragraph["text"]}]}
        project = adaptations.submit_analysis(project["id"], chunk["id"], analysis, project["revision"])
    return project


def make_plan(units=2):
    return {"logline": "许愿者与心魔交换身份，代价不能撤回。", "synopsis": "主角许愿获得力量，却失去亲人对他的记忆，最终主动承担代价。",
            "bible": {"setting": "临海宗门", "tone": "克制悬疑", "naming_strategy": "全名、名与别名统一为中文姓名；歧义称谓按上下文。",
                      "characters": [{"id": "lin", "source_names": ["Henry Jekyll", "Jekyll"], "target_name": "林照", "target_aliases": ["阿照"],
                                      "role": "修炼者", "motivation": "挽救亲人", "arc": "从逃避到承担", "relationships": ["心魔与主角共享身体"]}],
                      "world_rules": [{"id": "wish", "rule": "愿望交换记忆", "cost": "失去一段关系", "limit": "最多三次"}],
                      "immutable_facts": ["已经支付的代价不能收回"]},
            "units": [{"id": f"u{i}", "title": f"第{i}章", "source_chapter_ids": [f"ch{i:04d}"] if units == 2 else ["ch0001", "ch0002"],
                       "objective": "获得力量", "conflict": "力量需要代价", "turning_point": "失去记忆", "cliffhanger": "谁付出了代价？", "beats": ["许愿", "失去关系"]} for i in range(1, units + 1)]}


def draft_for(adaptations, project, unit_id, suffix=""):
    context = adaptations.context(project["id"], "write", unit_id=unit_id)
    return {"title": f"心魔契 · {unit_id}",
            "paragraphs": ["林照站在废弃的宗门门口，手中的命牌浮现一道裂纹。他想救回师兄，却不愿让村中任何人付出代价。契约只允许三次交换，每次都必须失去一段关系。他收回手，决定先查清命牌的来历。" + suffix],
            "summary": "林照发现命牌的限制，暂缓许愿。", "continuity_notes": ["命牌尚未使用", "最多三次交换"],
            "change_notes": ["将原作双重身份转化为命牌交易"], "source_chunk_ids": context["required_source_chunk_ids"]}


def review_for(adaptations, project, unit_id, passed=True):
    context = adaptations.context(project["id"], "review", unit_id=unit_id)
    return {"draft_revision": context["unit"]["draft_revision"], "reviewed_chunk_ids": context["required_review_chunk_ids"],
            "summary": "姓名、规则与因果已核对。", "checks": {key: passed for key in ("names", "world_rules", "causality", "continuity", "brief", "source_traceability", "framework_fit")},
            "findings": [] if passed else [{"category": key, "severity": "error", "message": "需要修订并重审。"} for key in ("names", "world_rules", "causality", "continuity", "brief", "source_traceability", "framework_fit")]}


def write_all(adaptations, project):
    for unit in project["units"]:
        project = adaptations.submit_draft(project["id"], unit["id"], draft_for(adaptations, project, unit["id"]), project["revision"])
    return project


def review_all(adaptations, project):
    for unit in project["units"]:
        project = adaptations.submit_review(project["id"], unit["id"], review_for(adaptations, project, unit["id"]), project["revision"])
    return project


@pytest.mark.parametrize("encoding", ["utf-8-sig", "gb18030", "utf-16"])
def test_txt_original_bytes_hash_encoding_and_chapter_boundaries(tmp_path, encoding):
    studio = Studio(Settings(data_dir=tmp_path, _env_file=None))
    source = "第一回 异国\n唐敖来到异国。\n第二回\n多九公辨认规则。".encode(encoding)
    book = studio.import_book(source, "镜花缘选章.txt")
    assert book["chapter_count"] == 2
    assert book["chapters"][0]["title"] == "第一回 异国"
    assert book["source_sha256"] == hashlib.sha256(source).hexdigest()
    assert studio.original(book["id"])[0] == source
    parsed = parse_epub((studio.store.directory / book['id'] / 'original.epub').read_bytes(), 200 * 1024 * 1024)
    assert '唐敖' in parsed['chapters'][0]['paragraphs'][1]['text']
    assert '多九公' in parsed['chapters'][1]['paragraphs'][1]['text']


def test_source_analysis_evidence_coverage_revision_and_retry(workspace):
    _, _, adaptations = workspace
    project = create_project(workspace)
    with pytest.raises(ValueError, match="完整分析"):
        adaptations.save_plan(project["id"], make_plan(), project["revision"])
    context = adaptations.context(project["id"])
    chunk = context["items"][0]
    analysis = {"summary": "主角许愿", "setting": "旧宅", "plot_beats": ["许愿"],
                "evidence": [{"paragraph_id": "p99999", "quote": "编造证据"}]}
    with pytest.raises(ValueError, match="证据"):
        adaptations.submit_analysis(project["id"], chunk["id"], analysis, project["revision"])
    assert adaptations.get(project["id"])["completed_chunks"] == 0
    paragraph = chunk["paragraphs"][-1]
    analysis["evidence"] = [{"paragraph_id": paragraph["id"], "quote": paragraph["text"]}]
    first = adaptations.submit_analysis(project["id"], chunk["id"], analysis, project["revision"])
    assert first["revision"] == 2
    assert adaptations.submit_analysis(project["id"], chunk["id"], analysis, project["revision"])["revision"] == 2
    with pytest.raises(ValueError, match="revision=2"):
        adaptations.submit_analysis(project["id"], chunk["id"], {**analysis, "summary": "新分析"}, 0)
    assert adaptations.context(project["id"])["items"][0]["chapter_id"] == "ch0002"
    # A new service object resumes the same persisted task.
    assert Adaptations(workspace[0]).get(project["id"])["completed_chunks"] == 1


def test_plan_scope_naming_and_power_system_requirements(workspace):
    _, _, adaptations = workspace
    project = analyze_all(adaptations, create_project(workspace, preset="xianxia_system"))
    plan = make_plan()
    with pytest.raises(ValueError, match="修仙"):
        adaptations.save_plan(project["id"], plan, project["revision"])
    plan["bible"]["power_system"] = {"realms": ["练气", "筑基"], "advancement": "修炼心法", "costs": ["寿元"], "limits": ["不能越阶"]}
    with pytest.raises(ValueError, match="系统流"):
        adaptations.save_plan(project["id"], plan, project["revision"])
    plan["bible"]["system_mechanics"] = {"name": "命牌", "trigger": "主动许愿", "abilities": ["交换力量"], "costs": ["关系记忆"], "limits": ["三次"]}
    bad = deepcopy(plan)
    bad["units"][1]["source_chapter_ids"] = ["ch9999"]
    with pytest.raises(ValueError, match="范围外"):
        adaptations.save_plan(project["id"], bad, project["revision"])
    bad = deepcopy(plan)
    bad["bible"]["characters"].append({**bad["bible"]["characters"][0], "id": "other"})
    with pytest.raises(ValueError, match="重名"):
        adaptations.save_plan(project["id"], bad, project["revision"])
    project = adaptations.save_plan(project["id"], plan, project["revision"])
    assert project["status"] == "writing"


def test_merge_split_and_documented_omissions(workspace):
    _, _, adaptations = workspace
    merged = analyze_all(adaptations, create_project(workspace, units=1))
    plan = make_plan(1)
    assert adaptations.save_plan(merged["id"], plan, merged["revision"])["status"] == "writing"
    omitted = analyze_all(adaptations, create_project(workspace, units=1))
    plan["units"][0]["source_chapter_ids"] = ["ch0001"]
    with pytest.raises(ValueError, match="删减原因"):
        adaptations.save_plan(omitted["id"], plan, omitted["revision"])
    plan["omitted_chapters"] = [{"chapter_id": "ch0002", "reason": "保留首章试播，暂不引入第二身份。"}]
    assert adaptations.save_plan(omitted["id"], plan, omitted["revision"])["status"] == "writing"


def test_draft_order_full_provenance_and_review_coverage(workspace):
    _, _, adaptations = workspace
    project = analyze_all(adaptations, create_project(workspace))
    project = adaptations.save_plan(project["id"], make_plan(), project["revision"])
    draft = draft_for(adaptations, project, "u2")
    with pytest.raises(ValueError, match="前面"):
        adaptations.submit_draft(project["id"], "u2", draft, project["revision"])
    draft = draft_for(adaptations, project, "u1")
    with pytest.raises(ValueError, match="本章全部"):
        adaptations.submit_draft(project["id"], "u1", {**draft, "source_chunk_ids": ["chunk99999"]}, project["revision"])
    with pytest.raises(ValueError, match="完整正文"):
        adaptations.submit_draft(project["id"], "u1", {**draft, "paragraphs": ["仅有梗概"]}, project["revision"])
    project = adaptations.submit_draft(project["id"], "u1", draft, project["revision"])
    with pytest.raises(ValueError, match="全部章节"):
        adaptations.submit_review(project["id"], "u1", review_for(adaptations, project, "u1"), project["revision"])
    project = adaptations.submit_draft(project["id"], "u2", draft_for(adaptations, project, "u2"), project["revision"])
    review = review_for(adaptations, project, "u1")
    with pytest.raises(ValueError, match="全部当前"):
        adaptations.submit_review(project["id"], "u1", {**review, "reviewed_chunk_ids": ["old"]}, project["revision"])
    with pytest.raises(ValueError, match="error"):
        adaptations.submit_review(project["id"], "u1", {**review, "checks": {**review["checks"], "names": False}}, project["revision"])
    project = adaptations.submit_review(project["id"], "u1", review_for(adaptations, project, "u1", False), project["revision"])
    with pytest.raises(ValueError, match="完整 Agent 审查"):
        adaptations.finalize(project["id"], "不能保存", project["revision"])


def test_upstream_revision_invalidates_downstream_memory_and_all_reviews(workspace):
    _, _, adaptations = workspace
    project = analyze_all(adaptations, create_project(workspace))
    project = adaptations.save_plan(project["id"], make_plan(), project["revision"])
    project = review_all(adaptations, write_all(adaptations, project))
    assert project["status"] == "ready"
    old_review = review_for(adaptations, project, "u1")
    project = adaptations.submit_draft(project["id"], "u1", draft_for(adaptations, project, "u1", "他藏起了命牌。"), project["revision"])
    assert project["status"] == "writing"
    assert project["units"][1]["continuity_stale"]
    assert all(u["review"] is None for u in project["units"])
    project = adaptations.submit_draft(project["id"], "u2", draft_for(adaptations, project, "u2"), project["revision"])
    with pytest.raises(ValueError, match="修订已过期"):
        adaptations.submit_review(project["id"], "u1", old_review, project["revision"])
    assert review_all(adaptations, project)["status"] == "ready"


def test_release_is_frozen_with_source_snapshot_and_epub_roundtrip(workspace):
    studio, book, adaptations = workspace
    studio.set_source(book["id"], {"language": "English", "edition": "原典试样", "rights_basis": "own_work"})
    project = analyze_all(adaptations, create_project(workspace))
    studio.set_source(book["id"], {"edition": "后来编辑的来源"})
    project = adaptations.save_plan(project["id"], make_plan(), project["revision"])
    project = review_all(adaptations, write_all(adaptations, project))
    release = adaptations.finalize(project["id"], "心魔契", project["revision"])
    assert adaptations.finalize(project["id"], "心魔契", 0) == release
    report = json.loads(adaptations.export(release["id"], "json")[0])
    assert report["source"]["edition"] == "原典试样"
    assert report["source_sha256"] == book["source_sha256"]
    assert len(report["units"]) == 2 and all(u["review"]["passed"] for u in report["units"])
    parsed = parse_epub(adaptations.export(release["id"], "epub")[0], 200 * 1024 * 1024)
    assert parsed["title"] == "心魔契" and len(parsed["chapters"]) == 2
    assert "林照" in parsed["chapters"][0]["paragraphs"][1]["text"]
    assert "# 心魔契" in adaptations.export(release["id"], "md")[0].decode("utf-8-sig")
    with pytest.raises(ValueError, match="已冻结"):
        adaptations.submit_draft(project["id"], "u1", draft_for(adaptations, project, "u1", "新结尾。"), adaptations.get(project["id"])["revision"])


def test_http_workflow_validation_catalog_and_guides(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        book = client.post("/api/books", files={"file": ("Test.txt", b"Chapter I\nHenry wishes.\nChapter II\nThe price arrives.")}).json()
        assert book["chapter_count"] == 2
        source = b"Chapter I\nHenry wishes.\nChapter II\nThe price arrives."
        assert client.get(f'/api/books/{book["id"]}/original').content == source
        assert len(client.get("/api/source-catalog").json()["works"]) == 10
        for section in ("brief", "analysis", "plan", "write", "review", "source"):
            assert "schema" in client.get("/api/adaptation-guide", params={"section": section}).json()
        invalid = client.post(f'/api/books/{book["id"]}/adaptations', json={"name": "错误项目", "chapter_ids": [], "brief": {"idea": "改编"}})
        assert invalid.status_code == 422
        assert "execution" in adaptation_guide()
        assert client.get("/api/adaptations/missing").status_code == 404


def test_long_draft_pagination_and_reviews_cannot_skip_chunks(workspace):
    _, _, adaptations = workspace
    project = analyze_all(adaptations, create_project(workspace, units=1, unit_characters=16000))
    project = adaptations.save_plan(project["id"], make_plan(1), project["revision"])
    draft = draft_for(adaptations, project, "u1")
    draft["paragraphs"] = ["林照遵守命牌的约定。" * 1000, "他沿着潮水退去的方向继续寻找答案。" * 400]
    project = adaptations.submit_draft(project["id"], "u1", draft, project["revision"])
    context = adaptations.context(project["id"], "review", unit_id="u1")
    assert context["next_cursor"] is not None
    review = review_for(adaptations, project, "u1")
    review["reviewed_chunk_ids"] = [context["items"][0]["id"]]
    with pytest.raises(ValueError, match="全部当前"):
        adaptations.submit_review(project["id"], "u1", review, project["revision"])
    assert adaptations.get(project["id"])["status"] == "reviewing"


def republic_framework():
    return {"era": "民国时期", "time_span": "1920 年开篇，1934 年归来", "locations": ["华东虚构港城"],
            "historical_policy": "遵循时代与技术边界，人物和地方机构虚构。", "naming_policy": "全体采用中文姓名，同一人改身份仍属同一角色。",
            "characters": [{"id": "lin", "source_names": ["Henry Jekyll", "Jekyll"], "target_name": "林照", "target_aliases": ["阿照"], "role": "航运青年"}],
            "setting_mappings": [{"source": "海外庄园", "target": "港城商号", "rationale": "保留经济利益而迁移制度。"}],
            "plot_spine": ["无辜青年被熟人构陷", "权力者为自保牺牲青年"], "allowed_inventions": ["允许桥接情节"],
            "prohibited_elements": ["不可沿用法国宫廷和现代电子设备"], "forbidden_terms": ["拿破仑", "微信"], "scope_note": "只试改已选原章，不代表全书完成。"}


def test_framework_is_a_required_prior_stage_and_context_contract(workspace):
    _, book, adaptations = workspace
    project = adaptations.create(book["id"], {"name": "民国试改", "chapter_ids": ["ch0001", "ch0002"],
                                               "require_framework": True, "brief": {"idea": "民国本土化", "target_units": 2, "unit_characters": 100}})
    assert project["status"] == "framing"
    assert adaptations.context(project["id"])["stage"] == "framework"
    with pytest.raises(ValueError, match="锁定前置"):
        analyze_all(adaptations, project)
    project = adaptations.save_framework(project["id"], republic_framework(), False, project["revision"])
    assert project["status"] == "framing"
    project = adaptations.save_framework(project["id"], republic_framework(), True, project["revision"])
    assert project["status"] == "analyzing" and project["framework_confirmed_at"]
    assert adaptations.context(project["id"])["framework"]["era"] == "民国时期"
    assert adaptations.save_framework(project["id"], republic_framework(), True, 0)["revision"] == project["revision"]


def test_framework_changes_invalidate_dependent_analysis_and_obey_revision(workspace):
    _, _, adaptations = workspace
    project = create_project(workspace, lock_framework=False)
    project = adaptations.save_framework(project["id"], republic_framework(), True, project["revision"])
    project = analyze_all(adaptations, project)
    changed = {**republic_framework(), "time_span": "1921 年"}
    with pytest.raises(ValueError, match="revision"):
        adaptations.save_framework(project["id"], changed, True, 0)
    project = adaptations.save_framework(project["id"], changed, True, project["revision"])
    assert project["completed_chunks"] == 0 and project["status"] == "analyzing"
    assert project["framework_revision"] == 2


def test_framework_name_contract_forbidden_words_review_and_frozen_release(workspace):
    _, _, adaptations = workspace
    project = create_project(workspace, lock_framework=False)
    project = adaptations.save_framework(project["id"], republic_framework(), True, project["revision"])
    project = analyze_all(adaptations, project)
    plan = make_plan()
    plan["bible"]["characters"][0]["target_name"] = "擅改的姓名"
    with pytest.raises(ValueError, match="偏离前置框架"):
        adaptations.save_plan(project["id"], plan, project["revision"])
    project = adaptations.save_plan(project["id"], make_plan(), project["revision"])
    with pytest.raises(ValueError, match="框架已冻结"):
        adaptations.save_framework(project["id"], {**republic_framework(), "time_span": "1922 年"}, True, project["revision"])
    draft = draft_for(adaptations, project, "u1", "拿破仑走进屋里。")
    with pytest.raises(ValueError, match="框架禁用词"):
        adaptations.submit_draft(project["id"], "u1", draft, project["revision"])
    project = write_all(adaptations, project)
    review = review_for(adaptations, project, "u1")
    review["checks"].pop("framework_fit")
    with pytest.raises(ValueError, match="framework_fit"):
        adaptations.submit_review(project["id"], "u1", review, project["revision"])
    for unit in project["units"]:
        review = review_for(adaptations, project, unit["id"])
        review["checks"]["framework_fit"] = True
        project = adaptations.submit_review(project["id"], unit["id"], review, project["revision"])
    release = adaptations.finalize(project["id"], "民国试改", project["revision"])
    snapshot = json.loads(adaptations.export(release["id"], "json")[0])
    assert snapshot["framework"] == republic_framework()
    assert snapshot["framework_confirmed_at"]
