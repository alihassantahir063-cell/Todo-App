import { createContext, useCallback, useMemo, useState } from 'react'
import { CheckCircle2, X, XCircle } from 'lucide-react'

export const ToastContext = createContext(null)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const dismiss = useCallback((id) => setToasts((current) => current.filter((toast) => toast.id !== id)), [])
  const toast = useCallback((message, type = 'success') => {
    const id = `${Date.now()}-${Math.random()}`
    setToasts((current) => [...current, { id, message, type }])
    window.setTimeout(() => dismiss(id), 4000)
  }, [dismiss])
  const value = useMemo(() => ({ toast }), [toast])
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" aria-live="polite" aria-atomic="true">
        {toasts.map((item) => (
          <div key={item.id} className={`toast ${item.type}`} role="status">
            {item.type === 'error' ? <XCircle size={18} /> : <CheckCircle2 size={18} />}
            <span>{item.message}</span>
            <button className="icon-button" aria-label="Dismiss notification" onClick={() => dismiss(item.id)}><X size={16} /></button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
