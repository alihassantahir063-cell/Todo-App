import { CheckSquare } from 'lucide-react'
import { Outlet } from 'react-router-dom'

export default function AuthLayout() {
  return <main className="auth-shell">
    <section className="auth-aside"><div className="brand light"><span className="brand-mark"><CheckSquare size={21} /></span>daymark</div><div className="auth-pitch"><span className="eyebrow">Make space for what matters</span><h1>Small steps.<br /><em>Big momentum.</em></h1><p>A calmer way to organize your day, stay focused, and see your progress add up.</p><div className="auth-note"><span className="note-check"><CheckSquare size={16} /></span><span>Thoughtful planning, made simple.</span></div></div><div className="auth-aside-footer">Your day, with a little more clarity.</div></section>
    <section className="auth-content"><Outlet /></section>
  </main>
}
