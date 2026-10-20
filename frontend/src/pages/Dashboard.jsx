import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle2, Clock3, ListTodo, Plus, Search, Target } from 'lucide-react'
import { taskService } from '../services/taskService'
import { useAuth } from '../hooks/useAuth'
import { useDebounce } from '../hooks/useDebounce'
import { useDataRefresh } from '../hooks/useDataRefresh'
import { getErrorMessage } from '../utils/errors'
import { Button, Input, Skeleton, StatCard } from '../components/ui'
import TaskList from '../components/TaskList'

export default function Dashboard() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [data, setData] = useState(null)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const query = useDebounce(search)
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [summary, tasks] = await Promise.all([
        taskService.stats(),
        taskService.list({ page: 1, page_size: 5, search: query || undefined, status, sort_by: 'created_at', order: 'desc' }),
      ])
      setStats(summary); setData(tasks)
    } catch (err) { setError(getErrorMessage(err, 'Could not load your dashboard.')) }
    finally { setLoading(false) }
  }, [query, status])
  useEffect(() => { load() }, [load])
  useDataRefresh(load)
  const total = stats?.total ?? 0
  const completed = stats?.completed ?? 0
  const percent = stats?.completion_percentage ?? (total ? Math.round(completed / total * 100) : 0)
  return <div className="page-stack">
    <section className="welcome-row"><div><span className="eyebrow">YOUR OVERVIEW</span><h1>Good to see you, {user?.name?.split(' ')[0] || 'there'}<span className="wave">✦</span></h1><p>Here’s a little snapshot of how things are moving.</p></div><Link className="button primary" to="/tasks?new=1"><Plus size={17} /> Quick add task</Link></section>
    <section className="stats-grid">
      {loading ? [1, 2, 3, 4].map((n) => <Skeleton className="stat-skeleton" key={n} />) : <>
        <StatCard label="All tasks" value={stats?.total ?? 0} icon={ListTodo} tone="violet" note="Across your workspace" />
        <StatCard label="In progress" value={stats?.pending ?? 0} icon={Clock3} tone="amber" note="One step at a time" />
        <StatCard label="Completed" value={stats?.completed ?? 0} icon={CheckCircle2} tone="green" note="Look at you go" />
        <StatCard label="Overdue" value={stats?.overdue ?? 0} icon={Target} tone="rose" note="Ready for a check-in" />
      </>}
    </section>
    <section className="progress-card"><div className="progress-heading"><div><span className="eyebrow">YOUR MOMENTUM</span><h2>Progress adds up</h2></div><strong>{percent}%</strong></div><div className="progress-track" role="progressbar" aria-label="Task completion" aria-valuenow={percent} aria-valuemin="0" aria-valuemax="100"><span style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} /></div><p>{completed} of {total} tasks completed</p></section>
    <section className="panel"><div className="section-heading"><div><span className="eyebrow">STAY IN FLOW</span><h2>Recent tasks</h2></div><Link to="/tasks" className="text-link">View all <ArrowRight size={16} /></Link></div>
      <div className="filter-row dashboard-filters"><div className="search-box"><Search size={17} /><input aria-label="Search tasks by title" placeholder="Search your tasks…" value={search} onChange={(event) => setSearch(event.target.value)} /></div><div className="tabs" aria-label="Filter tasks">{['all', 'pending', 'completed'].map((item) => <button key={item} className={status === item ? 'selected' : ''} onClick={() => setStatus(item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}</div></div>
      <TaskList tasks={data?.items} loading={loading} error={error} retry={load} onRefresh={load} emptyTitle="A clear runway" emptyText="No tasks match this view. Add one when you’re ready." />
      {!loading && data?.items?.length > 0 && <div className="list-footer"><span>Showing {data.items.length} recent tasks</span><Link className="button secondary small" to="/tasks">All tasks <ArrowRight size={15} /></Link></div>}
    </section>
  </div>
}
