import { Link } from 'react-router-dom'
import { ArrowLeft, ShieldX } from 'lucide-react'

export function AccessDenied() {
  return <main className="standalone-state"><span className="state-icon warning"><ShieldX size={30} /></span><span className="eyebrow">403 · ACCESS DENIED</span><h1>This space is restricted</h1><p>Your account doesn’t have permission to view this page.</p><Link className="button primary" to="/dashboard"><ArrowLeft size={16} /> Back to my workspace</Link></main>
}

export function NotFound() {
  return <main className="standalone-state"><span className="eyebrow">404 · PAGE NOT FOUND</span><h1>We couldn’t find that page</h1><p>The link may be old, or the page may have moved.</p><Link className="button primary" to="/dashboard"><ArrowLeft size={16} /> Back to my workspace</Link></main>
}
