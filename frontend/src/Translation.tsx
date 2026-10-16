import { ArrowRight, BookOpen, CheckCircle2 } from 'lucide-react'
import type { Adaptation, AdaptationDraft, Comparison } from './types'

export function TranslationFlow({ project }: { project: Adaptation }) {
  return <section className="translation-flow adapt-card">
    <div className="adapt-section-heading"><div><span className="eyebrow">READ IT WHOLE. THEN MAKE IT YOURS.</span><h2>先完整翻译，再解析重写</h2></div><span className="badge badge-green">一章对应一章</span></div>
    <div className="rewrite-flow"><span>原文与段落</span><ArrowRight size={14} /><strong>完整中文译稿</strong><ArrowRight size={14} /><span>故事解析</span><ArrowRight size={14} /><span>编辑改编框架</span><ArrowRight size={14} /><span>独立深度重写</span></div>
    <p className="adapt-prose">当前阶段保留原作的时代、人物、场景、对白和情节顺序。篇幅随原章展开，逐段记录原文对应；译意准确与细节完整须另行审校。{project.release ? '所选范围的译稿已经冻结，可从上方“解析译稿并重写”建立新项目。' : '全部所选章节翻译和审校完成后，才能冻结译稿，建立独立的重写项目。'}</p>
  </section>
}

export function AlignedTranslation({ original, draft }: { original: Comparison | null; draft: AdaptationDraft | null }) {
  const translated = new Map(draft?.source_paragraph_ids?.map((id, i) => [id, draft.paragraphs[i]]))
  return <section className="translation-aligned">
    <div className="adapt-reading-heading"><span><BookOpen size={14} /> 原文 · 完整译文逐段对照</span><span>{original ? `${translated.size} / ${original.paragraphs.length} 段已对齐` : '载入原文…'}</span></div>
    <div className="translation-aligned-body">{original?.paragraphs.map(p => <div className="translation-pair" key={p.id}><div><small>原文 · {p.id}</small><p>{p.original}</p></div><div><small>{translated.has(p.id) ? <CheckCircle2 size={12} /> : null} 译文</small><p>{translated.get(p.id) || '等待 Codex 提交完整译文'}</p></div></div>)}</div>
    {!!original?.layout_notes?.length && <details className="translation-layout"><summary>另行记录的 {original.layout_notes.length} 项版面信息</summary>{original.layout_notes.map(n => <p key={n.paragraph_id}>{n.paragraph_id} · {n.kind === 'heading' ? '章节标题（显示于目录）' : n.kind === 'illustration_caption' ? '原版插图说明' : '原版插图占位'}：{n.text}</p>)}<p>这些条目保留在来源记录中，不计为小说正文段落。</p></details>}
  </section>
}
