import { useEffect, useState } from 'react'
import { ArrowDownToLine, ArrowLeft, ArrowRight, BookOpen, Check, CheckCircle2, Copy, FileText, GitBranch, Loader2, Pencil, ScrollText, ShieldCheck, Sparkles } from 'lucide-react'
import { api, post } from './api'
import { CopyBlock, Modal } from './components'
import { FrameworkPanel } from './Framework'
import { RewriteEditor, RewritePanel } from './DeepRewrite'
import { TranslationFlow, AlignedTranslation } from './Translation'
import type { Adaptation, AdaptationBrief, AdaptationDraft, AdaptationUnit, Book, BookSource, Comparison, Handoff, SourceCatalog, StoryBible } from './types'

export const statusNames = { framing: '编辑条件', analyzing: '原著分析', planning: '设定大纲', writing: '章节改写', reviewing: '全文审查', auditing: '全书差异审查', ready: '等待保存', completed: '已完成' }
const deepStatusNames: Record<string, string> = { analyzing: '全稿诊断', planning: '全书重构', writing: '深度重写', reviewing: '逐章审查' }
const translationStatusNames: Record<string, string> = { framing: '翻译约定', planning: '翻译目录', writing: '逐章全译', reviewing: '译文审校' }
export const projectStatus = (project: Adaptation) => (project.mode === 'deep_rewrite' ? deepStatusNames[project.status] : project.mode === 'translation' ? translationStatusNames[project.status] : undefined) || statusNames[project.status]
export const projectStages = (project: Adaptation) => ['framing', ...(project.mode === 'translation' ? [] : ['analyzing']), 'planning', 'writing', 'reviewing', ...(project.mode === 'deep_rewrite' ? ['auditing'] : []), 'ready', 'completed']
const checkNames: Record<string, string> = { names: '姓名与称谓', world_rules: '世界规则', causality: '情节因果', continuity: '前后连续性', brief: '创作需求', source_traceability: '来源对应', framework_fit: '框架与时代', structural_change: '结构实质变化', independent_expression: '独立场景与表达', translation_fidelity: '译意准确', translation_completeness: '细节完整' }
const actionNames: Record<string, string> = { update_brief: '修改创作需求', save_framework: '保存框架草案', confirm_framework: '锁定改编条件', source_analysis: '参考稿分块分析', save_plan: '保存设定与大纲', submit_draft: '保存章节稿件', submit_review: '提交章节审查', rewrite_audit: '提交全书差异审查', finalize: '保存独立版本' }
const date = (value: string) => new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(value))
const lines = (value: string) => value.split('\n').map(v => v.trim()).filter(Boolean)

export function ProjectPage({ projectId, books, catalog, onUpdate, onBook, onBack, onOpen, notify }: {
  projectId: string; books: Book[]; catalog: SourceCatalog | null; onUpdate: (project: Adaptation) => void;
  onBook: (book: Book) => void; onBack: () => void; onOpen: (id: string) => void; notify: (text: string, error?: boolean) => void;
}) {
  const [project, setProject] = useState<Adaptation | null>(null)
  const [error, setError] = useState('')
  const [view, setView] = useState<'conditions' | 'overview' | 'bible' | 'chapters' | 'history' | 'rewrite'>('conditions')
  const [handoff, setHandoff] = useState<Handoff | null>(null)
  const [editing, setEditing] = useState<Adaptation | null>(null)
  const [rewriteEditing, setRewriteEditing] = useState<{ project: Adaptation; editing: boolean } | null>(null)
  const [scope, setScope] = useState<string[]>([])
  const [sourceOpen, setSourceOpen] = useState(false)
  const [frameworkEditing, setFrameworkEditing] = useState(false)
  const [busy, setBusy] = useState(false)
  const book = books.find(b => b.id === project?.book_id)
  const deep = project?.mode === 'deep_rewrite'
  const translating = project?.mode === 'translation'
  const referenceChapters = deep ? project.reference_chapters || [] : book?.chapters || []
  const editRequirements = () => {
    if (!project) return
    if (deep) setRewriteEditing({ project, editing: true })
    else { setEditing(project); setScope(project.chapter_ids) }
  }
  const accept = (next: Adaptation) => { setProject(next); onUpdate(next) }
  useEffect(() => {
    let cancelled = false, pending = false, first = true
    async function refresh() {
      if (pending) return
      pending = true
      try {
        const next = await api<Adaptation>(`/adaptations/${projectId}`)
        if (!cancelled) { setProject(next); setError(''); if (first) { setView(next.plan ? 'overview' : 'conditions'); first = false } }
      } catch (e) { if (!cancelled) setError((e as Error).message) }
      finally { pending = false }
    }
    void refresh(); const timer = setInterval(refresh, 4000)
    return () => { cancelled = true; clearInterval(timer) }
  }, [projectId])
  async function act(action: () => Promise<void>) {
    setBusy(true)
    try { await action() } catch (e) { notify((e as Error).message, true) } finally { setBusy(false) }
  }
  async function duplicate() {
    if (!project) return
    const next = await post<Adaptation>(`/books/${project.book_id}/adaptations`, { name: `${project.name.slice(0, 108)} · 新方案`, brief: project.brief, chapter_ids: project.chapter_ids, framework: project.framework, mode: project.mode || 'adaptation' })
    onUpdate(next); onOpen(next.id); notify('已建立独立的新方案，可以编辑条件后再次交给 Codex。')
  }
  if (!project || !book) return <main className="adapt-main"><button className="text-button" onClick={onBack}><ArrowLeft size={15} />返回项目列表</button>{error ? <p className="form-error" role="alert">{error}</p> : <div className="page-loading"><Loader2 className="spin" /><p>正在打开改编项目…</p></div>}</main>
  return <main className="adapt-main project-detail">
    <button className="text-button project-back" onClick={onBack}><ArrowLeft size={15} />全部改编项目</button>
    <div className="project-detail-heading"><div><span className="eyebrow">YOUR NEXT CHAPTER</span><h1>{project.name}</h1><p>{deep ? '基于上版' : '参考'}《{project.book_title}》 · {project.chapter_ids.length} 个{deep ? '上版' : '原著'}章节 · 更新于 {date(project.updated_at)}</p></div><div className="project-heading-actions"><span className={`badge ${project.release ? 'badge-green' : 'badge-neutral'}`}>{projectStatus(project)}</span>{!deep && <button className="button button-secondary" disabled={busy} onClick={() => void act(duplicate)}><Copy size={15} />以此创建新项目</button>}{project.release && <button className="button button-primary" onClick={() => setRewriteEditing({ project, editing: false })}><GitBranch size={16} />{translating ? '解析译稿并重写' : '深度重写'}</button>}{!project.release && <button className="button button-primary" disabled={busy || !project.framework_confirmed || frameworkEditing || !!editing || !!rewriteEditing} onClick={() => void act(async () => setHandoff(await api<Handoff>(`/adaptations/${project.id}/handoff`)))}><Sparkles size={16} />交给 Codex {translating ? '全译' : deep ? '深度重写' : '改编'}</button>}</div></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    <ProjectProgress project={project} />
    {translating && <TranslationFlow project={project} />}
    {deep && <div className="rewrite-lineage project-lineage"><span>原著</span><ArrowRight size={14} /><button className="text-button" onClick={() => onOpen(project.parent_project_id!)}>{project.parent_mode === 'translation' ? '冻结译稿' : '上版'}《{project.parent_name}》</button><ArrowRight size={14} /><strong>解析后独立重写</strong></div>}
    {project.release && <div className="adapt-release"><CheckCircle2 size={23} /><div><strong>独立版本已保存</strong><p>{project.release.chapter_count} 章 · {project.release.character_count.toLocaleString()} 字符 · 条件与创作记录已冻结</p></div><div>{['epub','txt','md','json'].map(format => <a className={`button ${format === 'epub' ? 'button-primary' : 'button-secondary'}`} key={format} href={`/api/adaptation-versions/${project.release!.id}/export?format=${format}`}><ArrowDownToLine size={15} />{format === 'json' ? '创作记录' : format.toUpperCase()}</a>)}</div></div>}
    {!project.plan && <div className={`handoff-banner ${project.framework_confirmed ? 'is-ready' : ''}`}><span className="handoff-number">{project.framework_confirmed ? '02' : '01'}</span><div><strong>{project.framework_confirmed ? '条件已锁定，可以开始创作' : translating ? '先统一译名和全译规则' : deep ? '先约定这次重写要改变什么' : '先编辑你的改编条件'}</strong><p>{project.framework_confirmed ? '将项目任务复制到已连接 MCP 的 Codex 会话，分析、写作与审查会同步到这里。' : '写清想法、时代、人物与情节边界，保存并锁定后再交给 Codex。'}</p></div>{project.framework_confirmed && <button className="button button-secondary" disabled={busy || frameworkEditing || !!editing || !!rewriteEditing} onClick={() => void act(async () => setHandoff(await api<Handoff>(`/adaptations/${project.id}/handoff`)))}><Copy size={15} />复制{translating ? '全译' : deep ? '重写' : '改编'}任务</button>}</div>}
    <nav className="adapt-tabs" aria-label="项目内容">{([['conditions',translating ? '翻译约定' : '改编条件'], ...(deep ? [['rewrite','重构与差异'] as const] : []), ['overview','创作总览'],['bible','人物与世界'],['chapters',translating ? '目录与译文' : '大纲与正文'],['history','创作记录']] as const).map(([id,label]) => <button key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)}>{label}</button>)}</nav>
    {<div className="conditions-stack" hidden={view !== 'conditions'}><section className="adapt-card"><div className="adapt-section-heading"><div><span className="eyebrow">THE CREATIVE BRIEF</span><h2>创作需求与参考范围</h2></div>{!project.plan && <button className="button button-secondary" onClick={editRequirements}><Pencil size={15} />编辑创作需求</button>}</div><p className="adapt-idea">{project.brief.idea}</p><div className="adapt-tags"><span>{catalog?.presets.find(p => p.id === project.brief.preset)?.name || project.brief.preset}</span><span>{project.brief.target_language}</span><span>{translating ? `${project.brief.target_units} 个原章，一对一完整翻译 · 篇幅随原章` : `${project.brief.target_units} 章 × 约 ${project.brief.unit_characters} 字符`}</span></div><dl className="adapt-definition"><dt>读者与基调</dt><dd>{project.brief.audience} · {project.brief.tone}</dd><dt>姓名原则</dt><dd>{project.brief.naming_style}</dd><dt>希望保留</dt><dd>{project.brief.preserve.join('；') || '遵循框架主线'}</dd><dt>重点改变</dt><dd>{project.brief.change.join('；') || '遵循框架约定'}</dd><dt>创作限制</dt><dd>{project.brief.constraints.join('；') || '遵循框架边界'}</dd></dl><details className="adapt-beats"><summary>查看{deep ? '上版全部' : '所选'} {project.chapter_ids.length} 个章节</summary>{referenceChapters.filter(c => project.chapter_ids.includes(c.id)).map(c => <p key={c.id}>{c.title}</p>)}</details>{project.plan && <p className="framework-foot">{deep ? '这份条件已随重构方案冻结；修改稿件后会重新进行审查。' : '这份条件已随方案冻结。调整方向可使用“以此创建新项目”。'}</p>}</section><FrameworkPanel project={project} onEditingChange={setFrameworkEditing} onSave={next => { accept(next); notify(next.framework_confirmed ? '条件已锁定，可以交给 Codex 改编。' : '框架草案已保存。') }} /></div>}
    {view === 'rewrite' && deep && <RewritePanel project={project} onEdit={editRequirements} onParent={() => onOpen(project.parent_project_id!)} />}
    {view === 'overview' && <div className="adapt-overview"><section className="adapt-card"><span className="eyebrow">THE STORY DIRECTION</span><h2>{translating ? '按原章完整呈现' : project.plan ? '新的故事，从这里展开' : '下一步，从约定到故事'}</h2>{project.plan ? <><p className="adapt-logline">{project.plan.logline}</p><p className="adapt-prose">{project.plan.synopsis}</p></> : <div className="adapt-next"><GitBranch size={20} /><p>{project.next_action.instruction}</p></div>}{project.status === 'ready' && <button className="button button-primary" disabled={busy} onClick={() => void act(async () => { await post(`/adaptations/${project.id}/finalize`, {name: project.name, expected_revision: project.revision}); accept(await api<Adaptation>(`/adaptations/${project.id}`)); notify('独立版本已保存。') })}>保存独立版本<Check size={15} /></button>}</section><section className="adapt-card"><span className="eyebrow">THE ORIGINAL</span><h2>{book.title}</h2><p className="adapt-prose">{project.source.edition || '原著版本未填写'}</p><dl className="adapt-definition"><dt>原著作者</dt><dd>{project.source.author || book.author}</dd><dt>{translating ? '翻译范围' : '改编范围'}</dt><dd>{project.chapter_ids.length} 个{deep ? '上版章节' : '所选原章'}，{project.total_chunks} 个参考分块</dd><dt>来源记录</dt><dd>项目创建时保存来源与文件指纹，可在导出记录中追溯。</dd></dl><button className="text-button" onClick={() => setSourceOpen(true)}>查看原著来源<ArrowRight size={14} /></button></section></div>}
    {view === 'bible' && (project.plan ? <BibleView bible={project.plan.bible} /> : <div className="adapt-empty"><ScrollText size={30} /><h3>人物与世界将在方案完成后出现</h3><p>先在改编条件中约定人物身份、姓名与世界边界。</p></div>)}
    {view === 'chapters' && (project.plan ? <ChapterView project={project} chapters={referenceChapters} /> : <div className="adapt-empty"><BookOpen size={30} /><h3>大纲与正文，等待故事展开</h3><p>锁定条件并交给 Codex 后，章节将按创作进度出现在这里。</p></div>)}
    {view === 'history' && <section className="adapt-card"><h2>每次推进，都有记录</h2><div className="adapt-history">{[...project.events].reverse().map(event => <div key={event.revision}><span className="badge badge-neutral">r{event.revision}</span><strong>{actionNames[event.action] || event.action}{event.unit_id ? ` · ${project.units.find(u => u.id === event.unit_id)?.title || event.unit_id}` : ''}</strong><time>{date(event.at)}</time></div>)}{!project.events.length && <p className="adapt-prose">项目已创建，等待你完成前置条件。</p>}</div></section>}
    <footer className="adapt-footer"><ShieldCheck size={14} />从原著出发，每一次改编都有迹可循<span>续章 · 让经典继续生长</span></footer>
    {editing && <BriefEditor initialProject={editing} book={book} scope={scope} onScope={setScope} presets={catalog?.presets || []} onClose={() => setEditing(null)} onCreate={async (name, brief) => { accept(await api<Adaptation>(`/adaptations/${project.id}/brief`, { method: 'PUT', body: JSON.stringify({ name, brief, chapter_ids: scope, expected_revision: editing.revision }) })); setEditing(null); notify('创作需求已保存，请核对并重新锁定框架。') }} />}
    {rewriteEditing && <RewriteEditor project={rewriteEditing.project} editing={rewriteEditing.editing} onClose={() => setRewriteEditing(null)} onSaved={next => { setRewriteEditing(null); if (next.id === project.id) accept(next); else { onUpdate(next); onOpen(next.id) } notify("深度重写要求已保存，请核对并锁定框架。") }} />}
    {sourceOpen && <SourceEditor book={book} onClose={() => setSourceOpen(false)} onSave={next => { onBook(next); setSourceOpen(false); notify('原著来源已保存，新项目将使用更新后的来源。') }} />}
    {handoff && <Modal title="把这份约定交给 Codex" subtitle="复制任务到已连接 novelstudio MCP 的 Codex 会话，即可从当前进度继续。" onClose={() => setHandoff(null)} wide><div className="codex-modal-content"><div className="modal-note"><CheckCircle2 size={19} /><p>已锁定框架 v{handoff.framework_revision} · 项目修订 r{handoff.revision}。Codex 将读取保存的条件，{translating ? '逐章逐段完整翻译并审校，完成后再解析与重写' : deep ? '完成全稿诊断、全书重构、重写与差异审查' : '逐章创作并回写进度'}。</p></div><CopyBlock value={handoff.prompt} label={translating ? '复制 Codex 全译任务' : deep ? '复制 Codex 重写任务' : '复制 Codex 改编任务'} /><p className="handoff-help">页面负责保存和展示项目；复制任务后，在 Codex 会话中发送即可启动创作。</p><div className="modal-actions"><button className="button button-primary" onClick={() => { setHandoff(null); setView('overview') }}>查看创作进度<ArrowRight size={15} /></button></div></div></Modal>}
  </main>
}
function ProjectProgress({ project }: { project: Adaptation }) {
  const deep = project.mode === 'deep_rewrite'
  const translating = project.mode === 'translation'
  const current = projectStages(project).indexOf(project.status)
  const drafts = project.units.filter(u => u.draft && !u.continuity_stale).length
  const reviews = project.units.filter(u => u.review?.passed).length
  const steps = [
    [translating ? '翻译约定' : '框架约定', project.framework_confirmed ? '已锁定' : project.framework_required ? '待约定' : '沿用创作需求'],
    ...(translating ? [] : [[deep ? '全稿诊断' : '原著分析', `${project.completed_chunks} / ${project.total_chunks} 块`]]),
    [translating ? '一对一目录' : deep ? '全书重构' : '设定大纲', project.plan ? `${project.plan.bible.characters.length} 位角色` : translating ? '按原章顺序' : '等待分析完成'],
    [translating ? '逐章全译' : deep ? '深度重写' : '章节改写', `${drafts} / ${project.brief.target_units} 章`],
    [translating ? '译文审校' : deep ? '逐章审查' : '全文审查', `${reviews} / ${project.brief.target_units} 章`],
    ...(deep ? [['差异审查', project.rewrite_audit?.passed ? '本轮通过' : project.rewrite_audit ? '仍需修订' : '等待全稿']] : []),
    ['独立版本', project.release ? '已保存' : project.status === 'ready' ? '可保存' : '等待审查'],
  ]
  return <div className={`adapt-progress ${translating ? 'adapt-progress-translation' : deep ? 'adapt-progress-deep' : ''}`}>{steps.map(([title, detail], i) => <div className={`${current > i ? 'done' : ''} ${current === i ? 'current' : ''}`} key={title}><span>{current > i ? <Check size={14} /> : String(i + 1).padStart(2, '0')}</span><div><strong>{title}</strong><small>{detail}</small></div>{i < steps.length - 1 && <ArrowRight size={14} />}</div>)}</div>
}

function BibleView({ bible }: { bible: StoryBible }) {
  return <div className="adapt-bible"><section className="adapt-card"><span className="eyebrow">WORLD & CONSTANTS</span><h2>世界与不变的事实</h2><p className="adapt-prose">{bible.setting}</p><dl className="adapt-definition"><dt>叙事基调</dt><dd>{bible.tone}</dd><dt>命名约定</dt><dd>{bible.naming_strategy}</dd></dl><ul className="adapt-bullets">{bible.immutable_facts.map((fact, i) => <li key={i}>{fact}</li>)}</ul></section><section className="adapt-card"><span className="eyebrow">CHARACTER BIBLE</span><h2>人物，拥有新的选择</h2><div className="adapt-character-grid">{bible.characters.map(c => <article key={c.id}><span className="eyebrow">{c.source_names.join(' / ') || '新增角色'} →</span><h3>{c.target_name}</h3>{c.target_aliases.length > 0 && <small>别名：{c.target_aliases.join('、')}</small>}<p>{c.role}</p><dl className="adapt-definition"><dt>动机</dt><dd>{c.motivation}</dd><dt>弧线</dt><dd>{c.arc}</dd></dl>{c.relationships.map((r, i) => <p className="adapt-relationship" key={i}>{r}</p>)}</article>)}</div></section><section className="adapt-card"><span className="eyebrow">RULES HAVE CONSEQUENCES</span><h2>规则、代价与边界</h2><div className="adapt-rules">{bible.world_rules.map((rule, i) => <article key={rule.id}><span>{String(i + 1).padStart(2, '0')}</span><div><h3>{rule.rule}</h3><p><b>代价</b>{rule.cost}</p><p><b>限制</b>{rule.limit}</p></div></article>)}</div></section>{bible.power_system && <section className="adapt-card"><span className="eyebrow">CULTIVATION</span><h2>修炼体系</h2><div className="adapt-tags">{bible.power_system.realms.map(r => <span key={r}>{r}</span>)}</div><p className="adapt-prose">{bible.power_system.advancement}</p><dl className="adapt-definition"><dt>修炼代价</dt><dd>{bible.power_system.costs.join('；')}</dd><dt>能力上限</dt><dd>{bible.power_system.limits.join('；')}</dd></dl></section>}{bible.system_mechanics && <section className="adapt-card"><span className="eyebrow">SYSTEM MECHANICS</span><h2>{bible.system_mechanics.name}</h2><p className="adapt-prose">触发：{bible.system_mechanics.trigger}</p><dl className="adapt-definition"><dt>能力</dt><dd>{bible.system_mechanics.abilities.join('；')}</dd><dt>代价</dt><dd>{bible.system_mechanics.costs.join('；')}</dd><dt>限制</dt><dd>{bible.system_mechanics.limits.join('；')}</dd></dl></section>}</div>
}

function ChapterView({ project, chapters }: { project: Adaptation; chapters: Book['chapters'] }) {
  const [unitId, setUnitId] = useState(project.units[0]?.id || '')
  const outline = project.plan!.units.find(u => u.id === unitId)!
  const unit = project.units.find(u => u.id === unitId)!
  const [content, setContent] = useState<(Omit<AdaptationUnit, 'draft'> & { draft: AdaptationDraft | null }) | null>(null)
  const [original, setOriginal] = useState<Comparison | null>(null)
  const [sourceId, setSourceId] = useState(outline.source_chapter_ids[0])
  const [error, setError] = useState('')
  useEffect(() => { setSourceId(outline.source_chapter_ids[0]) }, [unitId])
  useEffect(() => {
    const controller = new AbortController()
    setContent(null); setError('')
    api<Omit<AdaptationUnit, 'draft'> & { draft: AdaptationDraft | null }>(`/adaptations/${project.id}/units/${unitId}`, { signal: controller.signal }).then(next => { if (!controller.signal.aborted) setContent(next) }).catch(e => { if (!controller.signal.aborted) setError(e.message) })
    return () => controller.abort()
  }, [project.id, unitId, project.revision])
  useEffect(() => {
    const controller = new AbortController()
    setOriginal(null)
    api<Comparison>(`/adaptations/${project.id}/source-chapters/${sourceId}`, { signal: controller.signal }).then(next => { if (!controller.signal.aborted) setOriginal(next) }).catch(e => { if (!controller.signal.aborted) setError(e.message) })
    return () => controller.abort()
  }, [project.id, sourceId])
  return <div className="adapt-chapters"><aside className="adapt-chapter-list">{project.units.map((u, i) => <button className={u.id === unitId ? 'active' : ''} key={u.id} onClick={() => setUnitId(u.id)}><span>{String(i + 1).padStart(2, '0')}</span><div><strong>{u.title}</strong><small>{u.continuity_stale ? '需更新连续性' : u.review?.passed ? 'Agent 审查通过' : u.draft ? `稿件 r${u.draft_revision}` : '等待改写'}</small></div>{u.review?.passed && <CheckCircle2 size={14} />}</button>)}{project.plan!.omitted_chapters.length > 0 && <details><summary>{project.mode === 'deep_rewrite' ? '删减的上版章节' : '删减的原章'}</summary>{project.plan!.omitted_chapters.map(c => <p key={c.chapter_id}>{chapters.find(ch => ch.id === c.chapter_id)?.title}：{c.reason}</p>)}</details>}</aside><div className="adapt-chapter-detail"><section className="adapt-card"><div className="adapt-section-heading"><h2>{outline.title}</h2><span className="badge badge-neutral">{unit.draft ? `${unit.draft.character_count} 字符 · r${unit.draft_revision}` : '大纲已保存'}</span></div><dl className="adapt-definition"><dt>目标与冲突</dt><dd>{outline.objective}<br />{outline.conflict}</dd><dt>关键转折</dt><dd>{outline.turning_point}</dd><dt>章末悬念</dt><dd>{outline.cliffhanger}</dd></dl><details className="adapt-beats"><summary>展开情节节拍</summary><ol>{outline.beats.map((beat, i) => <li key={i}>{beat}</li>)}</ol></details>{unit.continuity_stale && <p className="adapt-stale">前文章节已修订，本章需要根据新的连续性记忆更新。</p>}{unit.review && <div className="adapt-review"><div className="adapt-tags">{Object.entries(unit.review.checks).map(([key, passed]) => <span key={key} className={passed ? 'check-pass' : 'check-fail'}>{passed ? '✓' : '×'} {checkNames[key]}</span>)}</div><p>{unit.review.summary}</p>{unit.review.findings.map((f, i) => <p className={f.severity === 'error' ? 'form-error' : ''} key={i}>{checkNames[f.category]} · {f.message}</p>)}</div>}</section>{error && <p className="form-error" role="alert">{error}</p>}{project.mode === 'translation' ? <AlignedTranslation original={original} draft={content?.draft || null} /> : <div className="adapt-comparison"><section><div className="adapt-reading-heading"><span>{project.mode === 'deep_rewrite' ? project.parent_mode === 'translation' ? '冻结译稿' : '上版改编稿' : '原著参考'}</span><select aria-label={project.mode === 'deep_rewrite' ? '选择上版章节' : '选择参考原章'} value={sourceId} onChange={e => setSourceId(e.target.value)}>{outline.source_chapter_ids.map(id => <option key={id} value={id}>{chapters.find(c => c.id === id)?.title || id}</option>)}</select></div><div className="adapt-reading-body">{original ? original.paragraphs.map(p => <p key={p.id}>{p.original}</p>) : <p>载入参考稿…</p>}</div></section><section><div className="adapt-reading-heading"><span>{project.mode === 'deep_rewrite' ? '深度重写正文' : '改编正文'}</span><span>{content?.draft ? '独立稿件' : '等待 Codex 提交'}</span></div><div className="adapt-reading-body">{content?.draft ? content.draft.paragraphs.map((p, i) => <p key={i}>{p}</p>) : <div className="adapt-empty"><FileText size={28} /><p>按大纲完成的正文会显示在这里。</p></div>}</div></section></div>}{content?.draft && <section className="adapt-card"><h3>本章留下的连续性记忆</h3><ul className="adapt-bullets">{content.draft.continuity_notes.map((n, i) => <li key={i}>{n}</li>)}</ul><details className="adapt-beats"><summary>查看改编说明</summary>{content.draft.change_notes.map((n, i) => <p key={i}>{n}</p>)}</details></section>}</div></div>
}

export function BriefEditor({ book, scope, onScope, presets, onCreate, onClose, initialProject }: { initialProject?: Adaptation; book: Book; scope: string[]; onScope: (ids: string[]) => void; presets: SourceCatalog['presets']; onCreate: (name: string, brief: AdaptationBrief, mode: 'adaptation' | 'translation') => Promise<void>; onClose: () => void }) {
  const [mode, setMode] = useState<'adaptation' | 'translation'>(initialProject?.mode === 'translation' ? 'translation' : 'adaptation')
  const translating = mode === 'translation'
  const [name, setName] = useState(initialProject?.name || `${book.title} · 新编`)
  const [idea, setIdea] = useState(initialProject?.brief.idea || '')
  const [preset, setPreset] = useState(initialProject?.brief.preset || 'localize')
  const [naming, setNaming] = useState(initialProject?.brief.naming_style || '中文姓名，统一姓、名、别名、尊称与文化背景')
  const [language, setLanguage] = useState(initialProject?.brief.target_language || '简体中文')
  const [tone, setTone] = useState(initialProject?.brief.tone || '悬念清晰，人物动机可信，能力的代价真实影响选择')
  const [audience, setAudience] = useState(initialProject?.brief.audience || '成年读者')
  const [preserve, setPreserve] = useState(initialProject?.brief.preserve.join('\n') || '原作最核心的冲突与因果关系')
  const [change, setChange] = useState(initialProject?.brief.change.join('\n') || '人物姓名与文化背景\n世界观、能力机制和具体情节')
  const [constraints, setConstraints] = useState(initialProject?.brief.constraints.join('\n') || '遵守前置框架约定的时代、人物与剧情因果。')
  const [count, setCount] = useState(initialProject?.brief.target_units || 3)
  const [length, setLength] = useState(initialProject?.brief.unit_characters || 2000)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  function selectMode(next: 'adaptation' | 'translation') {
    setMode(next)
    setName(`${book.title} · ${next === 'translation' ? '逐章全译' : '新编'}`)
    setIdea(next === 'translation' ? '按原著目录一章对应一章完整翻译，保留场景、动作、对白与叙事顺序。冻结译稿后再解析并独立重写。' : '')
    setPreset(next === 'translation' ? 'custom' : 'localize')
    setNaming(next === 'translation' ? '沿用原作姓名，以统一中文音译呈现，不在译稿阶段换成中国姓名' : '中文姓名，统一姓、名、别名、尊称与文化背景')
    setTone(next === 'translation' ? '忠实、完整、自然；不缩写，不添写' : '悬念清晰，人物动机可信')
    setPreserve(next === 'translation' ? '全部场景、对白、动作、细节、视角与原有顺序' : '原作最核心的冲突与因果关系')
    setChange(next === 'translation' ? '只将原作语言转换为目标语言' : '人物姓名与文化背景\n世界观与具体情节')
    setConstraints(next === 'translation' ? '每个原章对应一章，逐段完整翻译；不得合并、删减、重排或提前做民国化。' : '遵守前置框架约定的时代、人物与剧情因果。')
  }
  return <Modal title={initialProject ? "编辑创作需求与参考范围" : "为原著开启一个新世界"} subtitle={initialProject ? "修改需求或范围后，需要重新锁定框架；依赖旧条件的分析将失效。" : "选好参考范围与创作需求，创建后在项目中完善改编条件。"} onClose={onClose} wide><form className="editor-form adapt-create-form" onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { await onCreate(name.trim(), { idea, preset, naming_style: naming, target_language: language, tone, audience, preserve: lines(preserve), change: lines(change), constraints: lines(constraints), target_units: translating ? scope.length : count, unit_characters: length }, mode) } catch (e) { setError((e as Error).message); setBusy(false) } }}><fieldset className="creation-mode"><legend>本次要做什么</legend><div><button type="button" disabled={!!initialProject} className={!translating ? 'active' : ''} onClick={() => selectMode('adaptation')}><strong>直接改编</strong><span>按框架设计人物、时代与剧情</span></button><button type="button" disabled={!!initialProject} className={translating ? 'active' : ''} onClick={() => selectMode('translation')}><strong>先逐章全译</strong><span>完整译稿 → 故事解析 → 独立重写</span></button></div><p>{translating ? '所选原章与译文章节一一对应；逐段对齐，篇幅随原章。冻结译稿后再编辑改编框架。' : '若希望完整读懂外文原作后再改编，请选择“先逐章全译”。'}</p></fieldset><label>项目名称<input value={name} onChange={e => setName(e.target.value)} required maxLength={120} /></label><fieldset className="adapt-scope"><legend>参考原章 · 已选择 {scope.length} / {book.chapter_count} 章</legend><div className="adapt-scope-actions"><button type="button" className="text-button" onClick={() => onScope(book.chapters.map(c => c.id))}>全选</button>{book.chapters.some(c => /^Chapter \d+\./.test(c.title)) && <button type="button" className="text-button" onClick={() => onScope(book.chapters.filter(c => /^Chapter \d+\./.test(c.title)).map(c => c.id))}>仅选 Chapter 正文</button>}<button type="button" className="text-button" onClick={() => onScope([])}>清空</button></div><div>{book.chapters.map(c => <label key={c.id}><input type="checkbox" checked={scope.includes(c.id)} onChange={e => onScope(e.target.checked ? [...scope, c.id] : scope.filter(id => id !== c.id))} /><span>{c.title}</span><small>{c.word_count.toLocaleString()} 字符</small></label>)}</div></fieldset>{!translating && <><label>改编方向</label><div className="adapt-preset-grid">{presets.map(p => <button type="button" className={preset === p.id ? 'active' : ''} key={p.id} onClick={() => setPreset(p.id)}><strong>{p.name}</strong><span>{p.description}</span>{preset === p.id && <Check size={14} />}</button>)}</div></>}<label>你的具体想法<textarea aria-label="你的具体想法" required rows={4} maxLength={6000} value={idea} onChange={e => setIdea(e.target.value)} placeholder="例如：把《猴爪》的三个愿望改成修仙世界的因果兑换系统。主角每获得一项能力，都要失去一段重要关系；保留三个愿望逐步失控的结构，重写人物和结局。" /></label><div className="name-fields"><label>目标章节数<input type="number" min={1} max={200} disabled={translating} required value={translating ? scope.length : count} onChange={e => setCount(Number(e.target.value))} /></label><label>{translating ? '参考字符数（全译不限篇幅）' : '每章目标字符数'}<input type="number" min={100} max={30000} step={100} disabled={translating} required value={length} onChange={e => setLength(Number(e.target.value))} /></label></div><div className="name-fields"><label>姓名策略<input value={naming} onChange={e => setNaming(e.target.value)} required maxLength={120} /></label><label>目标语言<input value={language} onChange={e => setLanguage(e.target.value)} required maxLength={120} /></label></div><div className="name-fields"><label>目标读者<input value={audience} onChange={e => setAudience(e.target.value)} required maxLength={120} /></label><label>叙事基调<input value={tone} onChange={e => setTone(e.target.value)} required maxLength={120} /></label></div><div className="name-fields"><label>希望保留（每行一项）<textarea aria-label="希望保留（每行一项）" rows={3} value={preserve} onChange={e => setPreserve(e.target.value)} /></label><label>重点改变（每行一项）<textarea aria-label="重点改变（每行一项）" rows={3} value={change} onChange={e => setChange(e.target.value)} /></label></div><label>创作限制（每行一项）<textarea aria-label="创作限制（每行一项）" rows={2} value={constraints} onChange={e => setConstraints(e.target.value)} /></label>{error && <p className="form-error" role="alert">{error}</p>}<div className="modal-actions"><button type="button" className="button button-secondary" disabled={busy} onClick={onClose}>取消</button><button className="button button-primary" disabled={busy || !scope.length}>{busy ? <Loader2 size={16} className="spin" /> : <Sparkles size={16} />}{initialProject ? "保存创作需求" : "创建并编辑条件"}<ArrowRight size={16} /></button></div></form></Modal>
}

export function SourceEditor({ book, onClose, onSave }: { book: Book; onClose: () => void; onSave: (book: Book) => void }) {
  const [source, setSource] = useState<BookSource>({ language: '', edition: '', translator: '', source_url: '', rights_basis: 'unknown', territory: '', rights_note: '', ...book.source, title: book.source?.title || book.title, author: book.source?.author || book.author })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const field = (key: keyof BookSource, value: string) => setSource(s => ({ ...s, [key]: value }))
  return <Modal title="记录这份原著的来处" subtitle="区分原作、具体版本与翻译。新建改编项目时会保留这份记录。" onClose={onClose}><form className="editor-form" onSubmit={async e => { e.preventDefault(); setBusy(true); setError(''); try { onSave(await api<Book>(`/books/${book.id}/source`, { method: 'PUT', body: JSON.stringify(source) })) } catch (e) { setError((e as Error).message); setBusy(false) } }}><div className="name-fields"><label>原著书名<input value={source.title || ''} onChange={e => field('title', e.target.value)} maxLength={300} /></label><label>原著作者<input value={source.author || ''} onChange={e => field('author', e.target.value)} maxLength={300} /></label></div><label>版本说明<input value={source.edition} onChange={e => field('edition', e.target.value)} maxLength={500} placeholder="如：清代原典 / Gutenberg 英文原文" /></label><div className="name-fields"><label>原文语言<input value={source.language} onChange={e => field('language', e.target.value)} maxLength={80} /></label><label>译者（原文可留空）<input value={source.translator} onChange={e => field('translator', e.target.value)} maxLength={200} /></label></div><label>来源链接<input type="url" value={source.source_url} onChange={e => field('source_url', e.target.value)} maxLength={2000} placeholder="https://…" /></label><div className="name-fields"><label>使用依据<select aria-label="使用依据" value={source.rights_basis} onChange={e => field('rights_basis', e.target.value)}><option value="unknown">待记录</option><option value="public_domain">公版原作 / 版本</option><option value="permission">已获授权</option><option value="own_work">本人原创</option></select></label><label>使用地区<input value={source.territory} onChange={e => field('territory', e.target.value)} maxLength={200} placeholder="如：中国大陆" /></label></div><label>来源备注<textarea rows={3} value={source.rights_note} onChange={e => field('rights_note', e.target.value)} maxLength={2000} /></label><div className="modal-note"><FileText size={16} /><p>原作进入公版与现代译本的权利状态分别记录。此处保存你的来源说明。</p></div>{error && <p className="form-error" role="alert">{error}</p>}<div className="modal-actions"><button type="button" className="button button-secondary" disabled={busy} onClick={onClose}>取消</button><button className="button button-primary" disabled={busy}>{busy ? <Loader2 className="spin" size={15} /> : <Check size={15} />}保存来源</button></div></form></Modal>
}

