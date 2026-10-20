import { useEffect, useRef } from 'react'
import { forwardRef } from 'react'
import { Check, ChevronLeft, ChevronRight, LoaderCircle, X } from 'lucide-react'

export function Button({ children, variant = 'primary', className = '', type = 'button', ...props }) {
  return <button type={type} className={`button ${variant} ${className}`} {...props}>{children}</button>
}

export const Input = forwardRef(function Input({ label, error, className = '', ...props }, ref) {
  return (
    <label className={`field ${className}`}>
      {label && <span className="field-label">{label}</span>}
      <input ref={ref} className="input" aria-invalid={Boolean(error)} {...props} />
      {error && <span className="field-error">{error}</span>}
    </label>
  )
})

export const Select = forwardRef(function Select({ label, children, className = '', ...props }, ref) {
  return <label className={`field ${className}`}>
    {label && <span className="field-label">{label}</span>}
    <select ref={ref} className="input" {...props}>{children}</select>
  </label>
})

export function Badge({ children, tone = 'neutral' }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

export function Skeleton({ className = '' }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />
}

export function FullPageLoader({ label = 'Loading…' }) {
  return <div className="full-loader"><LoaderCircle className="spin" size={28} /><span>{label}</span></div>
}

export function EmptyState({ title, description, action }) {
  return <div className="empty-state"><div className="empty-icon"><Check size={22} /></div><h3>{title}</h3><p>{description}</p>{action}</div>
}

export function StatCard({ label, value, icon: Icon, tone = 'violet', note }) {
  return <article className="stat-card">
    <div className={`stat-icon ${tone}`}>{Icon && <Icon size={19} />}</div>
    <p>{label}</p><strong>{value ?? '—'}</strong>{note && <small>{note}</small>}
  </article>
}

export function Pagination({ page, pages, total, pageSize, onChange }) {
  if (!pages || pages <= 1) return null
  return <div className="pagination">
    <span>{total} results · Page {page} of {pages}</span>
    <div className="pagination-actions">
      <Button variant="secondary" aria-label="Previous page" disabled={page <= 1} onClick={() => onChange(page - 1)}><ChevronLeft size={17} /> Previous</Button>
      <Button variant="secondary" aria-label="Next page" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next <ChevronRight size={17} /></Button>
    </div>
    <span className="sr-only">{pageSize} items per page</span>
  </div>
}

export function Modal({ open, onClose, title, children, size = '' }) {
  const dialogRef = useRef(null)
  useEffect(() => {
    if (!open) return undefined
    const previous = document.activeElement
    const dialog = dialogRef.current
    const focusable = () => [...dialog.querySelectorAll('button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')]
    focusable()[0]?.focus()
    const keyHandler = (event) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const items = focusable()
        if (!items.length) return
        const first = items[0]
        const last = items[items.length - 1]
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
      }
    }
    document.addEventListener('keydown', keyHandler)
    return () => { document.removeEventListener('keydown', keyHandler); previous?.focus() }
  }, [open, onClose])
  if (!open) return null
  return <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={dialogRef} className={`modal ${size}`} role="dialog" aria-modal="true" aria-labelledby="modal-title" tabIndex="-1">
      <header className="modal-header"><h2 id="modal-title">{title}</h2><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={19} /></button></header>
      {children}
    </section>
  </div>
}

export function ConfirmDialog({ open, title, description, confirmLabel = 'Confirm', busy, onConfirm, onClose, danger = false }) {
  return <Modal open={open} onClose={onClose} title={title}>
    <div className="modal-body"><p>{description}</p></div>
    <footer className="modal-footer"><Button variant="secondary" onClick={onClose} disabled={busy}>Cancel</Button><Button variant={danger ? 'danger' : 'primary'} onClick={onConfirm} disabled={busy}>{busy && <LoaderCircle className="spin" size={16} />}{confirmLabel}</Button></footer>
  </Modal>
}
