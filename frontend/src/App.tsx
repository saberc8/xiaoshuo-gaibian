import { useEffect, useRef, useState } from 'react'
import { BookOpen, Cable, CheckCircle2, FolderOpen, Loader2, Plus, X } from 'lucide-react'
import { api } from './api'
import { ProjectPage, BriefEditor, SourceEditor } from './Adaptation'
import { ProjectList, LibraryPage, SettingsPage } from './Pages'
import { Modal } from './components'
import type { Adaptation, AdaptationBrief, Book, SourceCatalog, SystemInfo } from './types'

const go = (path: string) => { window.location.hash = path }
const route = () => window.location.hash.slice(1) || '/projects'

export default function App() {
  const [path, setPath] = useState(route)
  const [books, setBooks] = useState<Book[]>([])
  const [projects, setProjects] = useState<Adaptation[]>([])
  const [catalog, setCatalog] = useState<SourceCatalog | null>(null)
  const [system, setSystem] = useState<SystemInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [newProject, setNewProject] = useState<{ bookId: string } | null>(null)
  const [sourceBook, setSourceBook] = useState<Book | null>(null)
  const [toast, setToast] = useState<{ text: string; error: boolean } | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const toastTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const projectId = path.startsWith('/projects/') ? path.split('/')[2] : ''
  function notify(text: string, error = false) {
    setToast({ text, error }); clearTimeout(toastTimer.current)
    toastTimer.current = setTimeout(() => setToast(null), 6000)
  }
  async function refresh() {
    try {
      const [nextBooks, nextProjects, nextSystem, nextCatalog] = await Promise.all([
        api<Book[]>('/books'), api<Adaptation[]>('/adaptations'), api<SystemInfo>('/system'), api<SourceCatalog>('/source-catalog'),
      ])
      setBooks(nextBooks); setProjects(nextProjects); setSystem(nextSystem); setCatalog(nextCatalog); setError('')
    } catch (e) { setError((e as Error).message) }
    finally { setLoading(false) }
  }
  useEffect(() => {
    const changed = () => { setPath(route()); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', changed); void refresh()
    return () => { window.removeEventListener('hashchange', changed); clearTimeout(toastTimer.current) }
  }, [])
  useEffect(() => {
    if (path !== '/projects') return
    let cancelled = false, busy = false
    const timer = setInterval(async () => {
      if (busy) return
      busy = true
      try { const next = await api<Adaptation[]>('/adaptations'); if (!cancelled) { setProjects(next); setError('') } }
      catch (e) { if (!cancelled) setError((e as Error).message) }
      finally { busy = false }
    }, 4000)
    return () => { cancelled = true; clearInterval(timer) }
  }, [path])
  useEffect(() => {
    const title = projects.find(p => p.id === projectId)?.name
    document.title = title ? `${title} · 续章` : '续章 · 小说改编工作台'
  }, [projectId, projects])
  const updateProject = (next: Adaptation) => setProjects(current => [next, ...current.filter(p => p.id !== next.id)])
  const updateBook = (next: Book) => setBooks(current => [next, ...current.filter(b => b.id !== next.id)])
  async function upload(file: File) {
    setUploading(true)
    try {
      const form = new FormData(); form.append('file', file)
      const book = await api<Book>('/books', { method: 'POST', body: form })
      updateBook(book); setNewProject({ bookId: book.id }); notify('原著已导入，选择参考章节即可建立改编项目。')
    } catch (e) { notify((e as Error).message, true) }
    finally { setUploading(false); if (input.current) input.current.value = '' }
  }
  return <div className="app-shell">
    <input ref={input} type="file" accept=".epub,.txt" className="visually-hidden" aria-label="上传 EPUB 或 TXT 原著" onChange={e => { const file = e.target.files?.[0]; if (file) void upload(file) }} />
    <header className="app-header"><button className="brand" onClick={() => go('/projects')} aria-label="续章首页"><span className="brand-mark"><BookOpen size={23} strokeWidth={1.5} /></span><span className="brand-name">续章<span>XUZHANG</span></span></button><nav className="main-nav" aria-label="主导航">
      <button className={path.startsWith('/projects') ? 'active' : ''} onClick={() => go('/projects')}><FolderOpen size={16} />改编项目</button>
      <button className={path === '/library' ? 'active' : ''} onClick={() => go('/library')}><BookOpen size={16} />原著书架</button>
      <button className={path === '/settings' ? 'active' : ''} onClick={() => go('/settings')}><Cable size={16} />连接与设置</button>
    </nav><div className="header-actions"><button className="button button-dark" onClick={() => input.current?.click()} disabled={uploading}>{uploading ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}导入原著</button></div></header>
    {error && <div className="app-error" role="alert">{error}<button className="text-button" onClick={() => void refresh()}>重新连接</button></div>}
    {loading ? <main className="page-loading"><Loader2 className="spin" size={24} /><p>正在打开你的故事工作台…</p></main> : projectId ? <ProjectPage key={projectId} projectId={projectId} books={books} catalog={catalog} onUpdate={updateProject} onBook={updateBook} onBack={() => go('/projects')} onOpen={id => go(`/projects/${id}`)} notify={notify} /> : path === '/library' ? <LibraryPage books={books} catalog={catalog} onUpload={() => input.current?.click()} onCreate={bookId => setNewProject({ bookId })} onSource={setSourceBook} /> : path === '/settings' ? <SettingsPage system={system} online={!error} /> : <ProjectList projects={projects} books={books} onOpen={id => go(`/projects/${id}`)} onCreate={() => setNewProject({ bookId: '' })} onLibrary={() => go('/library')} />}
    {newProject && <CreateProject books={books} initialBookId={newProject.bookId} presets={catalog?.presets || []} onUpload={() => { setNewProject(null); input.current?.click() }} onClose={() => setNewProject(null)} onCreated={next => { updateProject(next); setNewProject(null); go(`/projects/${next.id}`); notify('项目已创建。完善改编条件并锁定后，即可交给 Codex。') }} />}
    {sourceBook && <SourceEditor book={sourceBook} onClose={() => setSourceBook(null)} onSave={next => { updateBook(next); setSourceBook(null); notify('原著来源已保存。') }} />}
    {toast && <div className={`toast ${toast.error ? 'toast-error' : ''}`} role={toast.error ? 'alert' : 'status'}>{toast.error ? <X size={17} /> : <CheckCircle2 size={17} />}<span>{toast.text}</span><button aria-label="关闭提示" onClick={() => setToast(null)}><X size={15} /></button></div>}
  </div>
}

function CreateProject({ books, initialBookId, presets, onUpload, onClose, onCreated }: { books: Book[]; initialBookId: string; presets: SourceCatalog['presets']; onUpload: () => void; onClose: () => void; onCreated: (project: Adaptation) => void }) {
  const [bookId, setBookId] = useState(initialBookId)
  const [scope, setScope] = useState<string[]>([])
  const book = books.find(b => b.id === bookId)
  async function create(name: string, brief: AdaptationBrief, mode: 'adaptation' | 'translation') {
    const next = await api<Adaptation>(`/books/${book!.id}/adaptations`, { method: 'POST', body: JSON.stringify({ name, brief, chapter_ids: scope, mode }) })
    onCreated(next)
  }
  if (book) return <BriefEditor book={book} scope={scope} onScope={setScope} presets={presets} onCreate={create} onClose={onClose} />
  return <Modal title="从哪一本原著出发？" subtitle="同一本原著可以建立多个改编项目，各自拥有独立的条件、正文和版本。" onClose={onClose} wide><div className="book-picker">{books.map(b => <button key={b.id} onClick={() => setBookId(b.id)}><BookOpen size={24} /><span><strong>{b.title}</strong><small>{b.author || '作者未填写'} · {b.chapter_count} 章</small></span><Plus size={16} /></button>)}<button className="book-picker-import" onClick={onUpload}><Plus size={22} /><span><strong>导入一本原著</strong><small>支持 EPUB / TXT，上传后选择章节</small></span></button></div></Modal>
}
