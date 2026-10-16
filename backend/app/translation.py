"""Faithful, aligned chapter translations before structural adaptation.

The translated edition is an immutable baseline for the existing rewrite flow.
Alignment proves paragraph coverage; fidelity remains an explicit agent review.
"""
import re


def translation_reference(book):
    """Separate proven layout markers without changing the stored original.

    Gutenberg's image-free EPUB exposes image link labels as text. Only labels
    with a matching image anchor are metadata; actual captions remain prose.
    Paragraph IDs stay intact so the original edition can still be cited.
    """
    chapters = []
    for chapter in book['chapters']:
        body, notes = [], []
        for paragraph in chapter['paragraphs']:
            text = paragraph['text'].strip()
            if text == chapter['title'].strip():
                notes.append({'paragraph_id': paragraph['id'], 'kind': 'heading', 'text': text})
            elif re.fullmatch(r'\[Illustration:.*\]', text, flags=re.DOTALL):
                notes.append({'paragraph_id': paragraph['id'], 'kind': 'illustration_caption', 'text': text})
            elif re.fullmatch(r'\d{4,6}[a-z]?', text) and any(a.startswith('img_images_') for a in paragraph.get('anchors', [])):
                notes.append({'paragraph_id': paragraph['id'], 'kind': 'illustration_marker', 'text': text})
            else:
                body.append(paragraph)
        chapters.append({**chapter, 'paragraphs': body, 'layout_notes': notes})
    return {**book, 'chapters': chapters}


def check_translation_scope(brief, chapter_ids):
    if brief['target_units'] != len(chapter_ids):
        raise ValueError('逐章全译的目标章数必须等于所选原章数，一章对应一章')
    if brief['preset'] != 'custom' or brief.get('rewrite'):
        raise ValueError('逐章全译使用 custom 方向；时代迁移与剧情改编在冻结译稿后的独立重写项目进行')


def check_translation_plan(project, plan):
    expected = [[chapter_id] for chapter_id in project['chapter_ids']]
    if [u['source_chapter_ids'] for u in plan['units']] != expected or plan['omitted_chapters']:
        raise ValueError('逐章全译须按原目录顺序一章对一章，不可合并、拆分、删减或重排')
    if plan['bible']['power_system'] or plan['bible']['system_mechanics']:
        raise ValueError('译稿须忠实于原作；新增能力或系统请在后续重写框架中约定')


def check_translation_draft(chapter, draft):
    expected = [p['id'] for p in chapter['paragraphs']]
    if draft.get('source_paragraph_ids') != expected or len(draft['paragraphs']) != len(expected):
        raise ValueError('逐章全译须为每个原文段落提交一段完整译文；source_paragraph_ids 必须按原顺序完整对应，不可漏段、并段或重复')


def translation_instructions():
    return [
        '这是忠实全译阶段。保留原作的姓名身份、年代地点、叙事顺序、场景、动作、对白与细节，不进行民国化或剧情重构，也不写摘要代替正文。',
        '先锁定译名与翻译约定，然后 save_adaptation_plan 保存与所选原章顺序完全相同的一对一目录；此阶段不要求先做结构分析。',
        '逐章分页读完 write 的全部原文。draft.paragraphs 与 source_paragraph_ids 等长，每段原文必须对应一段完整译文，顺序和段落编号必须一致；不得为凑目标篇幅缩写或添写。',
        '参考字符数不限制译稿篇幅。段落对齐只证明覆盖，不能证明没有删节或误译；必须逐段对照原文人工判断。',
        'review 除既有检查外，必须显式提交 translation_fidelity 和 translation_completeness，分别核对含义准确与细节完整；分页审查包含当前译文分块的原文对照。',
        '全部所选章翻译和审校完成后冻结译稿，再 create_deep_rewrite：解析完整译稿与原文，锁定新的改编框架，重构后写独立小说。试译只代表明确选择的试作范围，不代表全书完成。',
    ]
