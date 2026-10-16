import { useState } from 'react'
import { ArrowRight, Check, GitBranch, Loader2, Pencil, Sparkles } from 'lucide-react'
import { api } from './api'
import { Modal } from './components'
import type { Adaptation, BaselineEvidence } from './types'

export const rewriteDimensions: Record<string, string> = {
  motivation: '人物动机与主动选择', relationships: '人物关系与利益结构', conflict: '核心冲突与因果',
  plot_structure: '情节结构与揭示顺序', pov: '叙事视角', theme: '主题表达', ending: '高潮与结局', voice: '语言与场景表达',
}
const lines = (v: string) => v.split('\n').map(s => s.trim()).filter(Boolean)

export function RewriteEditor({ project, editing = false, onClose, onSaved }: { project: Adaptation; editing?: boolean; onClose: () => void; onSaved: (project: Adaptation) => void }) {
  const initial = editing ? project.brief.rewrite : null
  const [name, setName] = useState(editing ? project.name : `${project.name.slice(0, 102)} · 深度重写`)
  const [idea, setIdea] = useState(editing ? project.brief.idea : project.mode === 'translation' ? '先完整解析冻结译稿与原文，再依据新框架设计人物、时代、关系和剧情。保留核心情感，写出场景充分展开的独立小说。' : '在已完成改编稿基础上，重新设计人物的主动选择、利益关系与冲突因果，并重组全书情节。保留核心情感，写出有独立叙事的新作品。')
  const [dimensions, setDimensions] = useState(initial?.dimensions || ['motivation', 'relationships', 'conflict', 'plot_structure'])
  const [narrative, setNarrative] = useState(initial?.narrative_strategy || '允许合并、拆分和重排章节；从新的角色目标组织场景与揭示，不逐章对应原作。')
  const [ending, setEnding] = useState(initial?.ending_direction || '高潮由新的人物选择与冲突因果产生，结局兑现本稿的代价和主题。')
  const [preserve, setPreserve] = useState(editing ? project.brief.preserve.join('\n') : project.mode === 'translation' ? '原作核心情感与可追溯来源\n新的时代、姓名和身份关系在本次改编框架中约定' : '已确认的时代背景与命名原则\n核心情感主题；具体关系、行动和因果允许重构')
  const [avoid, setAvoid] = useState(initial?.avoid.join('\n') || '不能仅替换姓名、地名或近义词\n不逐章照搬相同事件与揭示顺序\n不以新增设定消除既有规则的代价')
  const [naming, setNaming] = useState(project.brief.naming_style)
  const [tone, setTone] = useState(project.brief.tone)
  const [count, setCount] = useState(project.brief.target_units)
  const [length, setLength] = useState(project.brief.unit_characters)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const valid = dimensions.filter(d => d !== 'voice').length >= 3 && dimensions.some(d => d === 'conflict' || d === 'plot_structure')
  return <Modal title={editing ? '编辑深度重写要求' : '让故事再往前一步'} subtitle={editing ? '保存后需重新核对并锁定框架；原有诊断会重新开始。' : `以《${project.name}》的已完成版本为起点，保留上版，建立独立的重写项目。`} onClose={onClose} wide>
    <form className="editor-form rewrite-form" onSubmit={async e => {
      e.preventDefault(); if (!valid) return; setBusy(true); setError('')
      const brief = { ...project.brief, idea, tone, naming_style: naming, preserve: lines(preserve), change: dimensions.map(d => rewriteDimensions[d]), constraints: lines(avoid), target_units: count, unit_characters: length,
        rewrite: { dimensions, narrative_strategy: narrative, ending_direction: ending, avoid: lines(avoid) } }
      try {
        const next = await api<Adaptation>(editing ? `/adaptations/${project.id}/brief` : `/adaptations/${project.id}/deep-rewrites`, {
          method: editing ? 'PUT' : 'POST', body: JSON.stringify(editing ? { name, brief, chapter_ids: project.chapter_ids, expected_revision: project.revision } : { name, brief }),
        }); onSaved(next)
      } catch (e) { setError((e as Error).message); setBusy(false) }
    }}>
      <div className="rewrite-flow"><span>全稿诊断</span><ArrowRight size={14} /><span>全书重构</span><ArrowRight size={14} /><span>深度重写</span><ArrowRight size={14} /><span>差异审查</span></div>
      <label>重写项目名称<input required maxLength={120} value={name} onChange={e => setName(e.target.value)} /></label>
      <label>这次希望写出怎样的新故事<textarea aria-label="这次希望写出怎样的新故事" required rows={4} maxLength={6000} value={idea} onChange={e => setIdea(e.target.value)} /></label>
      <fieldset className="rewrite-dimensions"><legend>需要实质重构的维度</legend><p>至少三个结构维度，包含核心冲突或情节结构；语言润色可以另外加入。</p><div>{Object.entries(rewriteDimensions).map(([id,label]) => <label key={id}><input type="checkbox" checked={dimensions.includes(id)} onChange={e => setDimensions(ds => e.target.checked ? [...ds,id] : ds.filter(d => d !== id))} />{label}</label>)}</div></fieldset>
      <label>必须保留的底线（每行一项）<textarea aria-label="必须保留的底线（每行一项）" rows={3} required value={preserve} onChange={e => setPreserve(e.target.value)} /></label>
      <label>叙事组织与视角<textarea aria-label="叙事组织与视角" rows={3} required maxLength={6000} value={narrative} onChange={e => setNarrative(e.target.value)} /></label>
      <label>高潮与结局方向<textarea aria-label="高潮与结局方向" rows={3} required maxLength={6000} value={ending} onChange={e => setEnding(e.target.value)} /></label>
      <label>避免沿用的内容或做法（每行一项）<textarea aria-label="避免沿用的内容或做法（每行一项）" rows={3} required value={avoid} onChange={e => setAvoid(e.target.value)} /></label>
      <label>重写稿的姓名与称谓策略<input required maxLength={120} value={naming} onChange={e => setNaming(e.target.value)} /></label>
      <label>重写稿的叙事基调<input required maxLength={120} value={tone} onChange={e => setTone(e.target.value)} /></label>
      <div className="name-fields"><label>重写后章节数<input required type="number" min={1} max={200} value={count} onChange={e => setCount(Number(e.target.value))} /></label><label>每章目标字符数<input required type="number" min={100} max={30000} value={length} onChange={e => setLength(Number(e.target.value))} /></label></div>
      <div className="modal-note"><GitBranch size={18} /><p>先完整诊断上版全部章节。新大纲可以合并、删减或重排；每项结构变化都需有原著、上版与新稿的证据。</p></div>
      {!valid && <p className="form-error">请至少选择三个结构维度，并包含核心冲突或情节结构。</p>}{error && <p className="form-error" role="alert">{error}</p>}
      <div className="modal-actions"><button type="button" className="button button-secondary" disabled={busy} onClick={onClose}>取消</button><button className="button button-primary" disabled={busy || !valid}>{busy ? <Loader2 size={16} className="spin" /> : <Sparkles size={16} />}{editing ? '保存重写要求' : '建立深度重写项目'}</button></div>
    </form>
  </Modal>
}

function Evidence({ items }: { items: BaselineEvidence[] }) {
  return <div className="rewrite-evidence">{items.map((item,i) => <blockquote key={i}><small>{item.source === 'original' ? '最初原著' : '冻结上版（译稿／改编稿）'} · {item.chapter_id} · {item.paragraph_id}</small><p>{item.quote}</p></blockquote>)}</div>
}

export function RewritePanel({ project, onEdit, onParent }: { project: Adaptation; onEdit: () => void; onParent: () => void }) {
  const requirements = project.brief.rewrite!
  const design = project.plan?.rewrite_design
  const audit = project.rewrite_audit
  return <div className="rewrite-panel"><section className="adapt-card"><div className="adapt-section-heading"><div><span className="eyebrow">A NEW STORY, WITH A TRACEABLE ORIGIN</span><h2>深度重写约定</h2></div>{!project.plan && <button className="button button-secondary" onClick={onEdit}><Pencil size={14} />编辑重写要求</button>}</div><div className="rewrite-lineage"><span>最初原著</span><ArrowRight size={14} /><button className="text-button" onClick={onParent}>{project.parent_name}</button><ArrowRight size={14} /><strong>当前重写稿</strong></div>{project.plan && !project.release && <p className="framework-foot">当前大纲已保存。若需重新设计大纲，可打开上版，另建一份深度重写项目。</p>}<div className="adapt-tags">{requirements.dimensions.map(d => <span key={d}>{rewriteDimensions[d]}</span>)}</div><dl className="adapt-definition"><dt>叙事组织</dt><dd>{requirements.narrative_strategy}</dd><dt>结局方向</dt><dd>{requirements.ending_direction}</dd><dt>必须保留</dt><dd>{project.brief.preserve.join('；')}</dd><dt>避免沿用</dt><dd>{requirements.avoid.join('；')}</dd></dl></section>
    <section className="adapt-card"><span className="eyebrow">STRUCTURE BEFORE SENTENCES</span><h2>全书重构方案</h2>{design ? <><p className="adapt-prose">{design.diagnosis}</p><dl className="adapt-definition"><dt>新叙事结构</dt><dd>{design.narrative_strategy}</dd><dt>新高潮结局</dt><dd>{design.ending}</dd></dl><div className="rewrite-changes">{design.changes.map(c => <article key={c.dimension}><h3>{rewriteDimensions[c.dimension]}</h3><div className="rewrite-before-after"><div><small>原有结构</small><p>{c.before}</p></div><div><small>重构方案</small><p>{c.after}</p></div></div><p className="adapt-prose">{c.reason}</p><small>落实章节：{c.target_unit_ids.map(id => project.units.find(u => u.id === id)?.title || id).join('、')}</small><details className="adapt-beats"><summary>查看原著与上版的依据</summary><Evidence items={c.evidence} /></details></article>)}</div><dl className="adapt-definition"><dt>保留</dt><dd>{design.retained_elements.join('；')}</dd><dt>移除</dt><dd>{design.removed_elements.join('；')}</dd></dl></> : <div className="adapt-empty"><GitBranch size={28} /><h3>先诊断全稿，再重构全书</h3><p>Codex 会逐项说明原有结构、新的设计、改变原因和落实章节，然后开始正文重写。</p></div>}</section>
    <section className="adapt-card"><div className="adapt-section-heading"><div><span className="eyebrow">COMPARE THE STORY, NOT JUST THE WORDS</span><h2>全书差异审查</h2></div>{audit && <span className={`badge ${audit.passed ? 'badge-green' : 'badge-amber'}`}>{audit.passed ? <Check size={13} /> : null}{audit.passed ? '本轮审查通过' : '仍需修订'}</span>}</div>{audit ? <><p className="adapt-prose">{audit.summary}</p><p className="rewrite-audit-coverage">本次覆盖 {Object.keys(audit.unit_revisions).length} 章 · {audit.reviewed_chunk_ids.length} 个正文分块 · {audit.comparisons.length} 项证据对照</p>{audit.comparisons.map((c,i) => <details className="rewrite-audit-item" key={i}><summary>{c.passed ? '✓' : '待修订'} {rewriteDimensions[c.dimension]} · {project.units.find(u => u.id === c.unit_id)?.title || c.unit_id}</summary><Evidence items={c.baseline} /><blockquote className="rewrite-new-evidence"><small>当前重写稿 · {c.paragraph_id}</small><p>{c.quote}</p></blockquote><p className="adapt-prose">{c.judgment}</p></details>)}{audit.remaining_risks.length > 0 && <><h3>仍需复核</h3><ul className="adapt-bullets">{audit.remaining_risks.map((r,i) => <li key={i}>{r}</li>)}</ul></>}</> : <p className="adapt-prose">完成正文和逐章审查后，Codex 将对照原著、上版改编和新稿，给出每个结构维度的正文证据。全书差异审查通过后才能保存新版本。</p>}<p className="framework-foot">报告记录创作差异与判断依据，供作者复核，不把相似度分数作为原创或平台审核保证。</p></section>
  </div>
}
