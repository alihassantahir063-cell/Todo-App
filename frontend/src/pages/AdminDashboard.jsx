import { useEffect, useState } from 'react'
import { Activity, CheckCircle2, Clock3, ListTodo, Users, UserRoundCheck } from 'lucide-react'
import { adminService } from '../services/adminService'
import { useDataRefresh } from '../hooks/useDataRefresh'
import { getErrorMessage } from '../utils/errors'
import { Badge, Skeleton, StatCard } from '../components/ui'
import { isOverdue } from '../components/TaskItem'

export default function AdminDashboard() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const load = async () => {
    setLoading(true); setError('')
    try { setData(await adminService.dashboard()) }
    catch (err) { setError(getErrorMessage(err, 'Could not load the admin dashboard.')) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])
  useDataRefresh(load)
  const stats = data || {}
  return <div className="page-stack">
    <section className="page-title-row"><div><span className="eyebrow">ADMIN WORKSPACE</span><h1>Overview</h1><p>A live view of your Daymark community.</p></div></section>
    {error && <div className="error-banner" role="alert">{error}<button className="text-link" onClick={load}>Retry</button></div>}
    <section className="stats-grid admin-stats">
      {loading ? [1, 2, 3, 4, 5, 6].map((n) => <Skeleton className="stat-skeleton" key={n} />) : <>
        <StatCard label="Total users" value={stats.total_users ?? 0} icon={Users} tone="violet" />
        <StatCard label="Active users" value={stats.active_users ?? 0} icon={UserRoundCheck} tone="green" />
        <StatCard label="Inactive users" value={stats.inactive_users ?? 0} icon={Activity} tone="rose" />
        <StatCard label="Total tasks" value={stats.total_tasks ?? 0} icon={ListTodo} tone="blue" />
        <StatCard label="Completed" value={stats.completed_tasks ?? stats.completed ?? 0} icon={CheckCircle2} tone="green" />
        <StatCard label="Pending" value={stats.pending_tasks ?? stats.pending ?? 0} icon={Clock3} tone="amber" />
      </>}
    </section>
    <div className="admin-recent-grid">
      <section className="panel"><div className="section-heading"><div><span className="eyebrow">COMMUNITY</span><h2>Recent users</h2></div><a className="text-link" href="/admin/users">View users</a></div>
        {loading ? <div className="recent-skeletons"><Skeleton /><Skeleton /><Skeleton /></div> : <div className="recent-list">{(stats.recent_users || []).map((person) => <div className="recent-row" key={person.id}><span className="avatar">{person.name?.slice(0, 1)?.toUpperCase()}</span><div className="recent-copy"><strong>{person.name}</strong><span>{person.email}</span></div><Badge tone={person.is_active ? 'success' : 'neutral'}>{person.is_active ? 'Active' : 'Inactive'}</Badge></div>)}
          {!stats.recent_users?.length && <p className="muted empty-inline">No users to display.</p>}</div>}
      </section>
      <section className="panel"><div className="section-heading"><div><span className="eyebrow">LATEST ACTIVITY</span><h2>Recent tasks</h2></div><a className="text-link" href="/admin/tasks">View tasks</a></div>
        {loading ? <div className="recent-skeletons"><Skeleton /><Skeleton /><Skeleton /></div> : <div className="recent-list">{(stats.recent_tasks || []).map((task) => <div className="recent-row task-recent" key={task.id}><span className={`recent-task-dot ${task.status}`} /><div className="recent-copy"><strong>{task.title}</strong><span>{task.owner?.name || task.user_name || task.user?.name || 'User'} · {task.created_at ? new Date(task.created_at).toLocaleDateString() : ''}</span></div><Badge tone={task.status === 'completed' ? 'success' : isOverdue(task) ? 'danger' : 'neutral'}>{isOverdue(task) ? 'Overdue' : task.status}</Badge></div>)}
          {!stats.recent_tasks?.length && <p className="muted empty-inline">No tasks to display.</p>}</div>}
      </section>
    </div>
  </div>
}
