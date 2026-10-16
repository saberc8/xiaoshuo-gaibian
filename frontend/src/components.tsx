import { useEffect, useRef, useState, type ReactNode } from 'react'
import { X, Check, Copy } from 'lucide-react'

export function Modal({ title, subtitle, children, onClose, wide = false }: {
  title: string; subtitle?: string; children: ReactNode; onClose: () => void; wide?: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null)
  const closeRef = useRef(onClose)
  closeRef.current = onClose
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const focusable = () => Array.from(ref.current?.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href]') || [])
    focusable()[0]?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeRef.current()
      if (event.key !== 'Tab') return
      const elements = focusable()
      const first = elements[0], last = elements[elements.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => { document.body.style.overflow = overflow; document.removeEventListener('keydown', onKey); previous?.focus() }
  }, [])
  return <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <div className={`modal ${wide ? 'modal-wide' : ''}`} role="dialog" aria-modal="true" aria-label={title} ref={ref}>
      <div className="modal-heading"><div><span className="eyebrow">XUZHANG</span><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div><button className="icon-button" aria-label="关闭弹窗" onClick={onClose}><X size={19} /></button></div>
      {children}
    </div>
  </div>
}

export function CopyBlock({ value, label = '复制', onCopy }: { value: string; label?: string; onCopy?: () => void }) {
  const [copied, setCopied] = useCopied()
  return <div className="copy-block"><pre>{value}</pre><button className="copy-button" onClick={async () => {
    try { await navigator.clipboard.writeText(value); setCopied(); onCopy?.() }
    catch { /* Text remains selectable if the browser denies clipboard access. */ }
  }}>{copied ? <Check size={14} /> : <Copy size={14} />}{copied ? '已复制' : label}</button></div>
}

function useCopied(): [boolean, () => void] {
  const [copied, setCopied] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  useEffect(() => () => clearTimeout(timer.current), [])
  return [copied, () => { setCopied(true); clearTimeout(timer.current); timer.current = setTimeout(() => setCopied(false), 2000) }]
}
