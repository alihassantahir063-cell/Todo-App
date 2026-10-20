import { useCallback, useEffect, useState } from 'react'
import { Search, Trash2 } from 'lucide-react'
import { adminService } from '../services/adminService'
import { useDebounce } from '../hooks/useDebounce'
import { useDataRefresh } from '../hooks/useDataRefresh'
import { useToast } from '../hooks/useToast'
import { getErrorMessage } from '../utils/errors'
import { Badge, Button, ConfirmDialog, Input, Pagination, Select, Skeleton } from '../components/ui'

const PAGE_SIZE = 10

export default function AdminTasks() {
  const toast = useToast()
  const [data, setData] = useState(null)
  const [search, setSearch] = useState('')
  const [userId, setUserId] = useState('')
  const [status, setStatus] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState(null)
  const [busy, setBusy] = useState(false)
  const query = useDebounce(search)
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      setData(await adminService.tasks({ user_id: userId || undefined, status: status || undefined, date_from: dateFrom || undefined, date_to: dateTo || undefined, search: query || undefined, page, page_size: PAGE_SIZE }))
    } catch (err) { setError(getErrorMessage(err, 'Could not load tasks.')) }
    finally { setLoading(false) }
  }, [query, userId, status, dateFrom, dateTo, page])
  useEffect(() => { load() }, [load])
  useDataRefresh(load)
  const resetPage = (setter, value) => { setter(value); setPage(1) }
  const remove = async () => {
    setBusy(true)
    try { await adminService.deleteTask(deleting.id); toast('Task deleted'); setDeleting(null); await load() }
    catch (err) { toast(getErrorMessage(err), 'error') }
    finally { setBusy(false) }
  }
  return <div className="page-stack">
    <section className="page-title-row"><div><span className="eyebrow">WORKSPACE CONTENT</span><h1>All tasks</h1><p>Review and manage tasks across user accounts.</p></div></section>
    <section className="panel">
      <div className="admin-task-filters">
        <div className="search-box grow"><Search size={17} /><input aria-label="Search task titles" placeholder="Search task titles…" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} /></div>
        <Input label="User ID" type="number" min="1" placeholder="Any user" value={userId} onChange={(event) => resetPage(setUserId, event.target.value)} />
        <Select label="Status" value={status} onChange={(event) => resetPage(setStatus, event.target.value)}><option value="">All statuses</option><option value="pending">Pending</option><option value="completed">Completed</option></Select>
        <Input label="From date" type="date" value={dateFrom} onChange={(event) => resetPage(setDateFrom, event.target.value)} />
        <Input label="To date" type="date" value={dateTo} onChange={(event) => resetPage(setDateTo, event.target.value)} />
      </div>
      {error && <div className="error-banner" role="alert">{error}<Button variant="secondary" onClick={load}>Retry</Button></div>}
      {loading ? <div className="table-skeleton">{[1, 2, 3, 4].map((n) => <Skeleton key={n} />)}</div> : <div className="table-scroll"><table className="data-table"><thead><tr><th>Task</th><th>Owner</th><th>Status</th><th>Priority</th><th>Due date</th><th>Created</th><th>Action</th></tr></thead><tbody>{(data?.items || []).map((task) => <tr key={task.id}><td><div className="task-table-copy"><strong>{task.title}</strong>{task.description && <span>{task.description}</span>}</div></td><td>{task.owner?.name || task.user_name || task.user?.name || `User ${task.user_id ?? '—'}`}</td><td><Badge tone={task.status === 'completed' ? 'success' : 'neutral'}>{task.status}</Badge></td><td><Badge tone={`priority-${task.priority}`}>{task.priority}</Badge></td><td>{task.due_date ? new Date(`${String(task.due_date).slice(0, 10)}T00:00:00`).toLocaleDateString() : '—'}</td><td>{task.created_at ? new Date(task.created_at).toLocaleDateString() : '—'}</td><td><Button variant="danger-ghost" className="small" aria-label={`Delete ${task.title}`} onClick={() => setDeleting(task)}><Trash2 size={15} /> Delete</Button></td></tr>)}</tbody></table>
        {!data?.items?.length && <div className="empty-inline">No tasks match these filters.</div>}</div>}
      <Pagination page={data?.page || page} pages={data?.pages || 0} total={data?.total || 0} pageSize={data?.page_size || PAGE_SIZE} onChange={setPage} />
    </section>
    <ConfirmDialog open={Boolean(deleting)} title="Delete this task?" description={`“${deleting?.title}” will be permanently deleted from the workspace.`} confirmLabel="Delete task" danger busy={busy} onClose={() => setDeleting(null)} onConfirm={remove} />
  </div>
}
