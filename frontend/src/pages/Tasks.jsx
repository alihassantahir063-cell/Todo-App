import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, Search, SlidersHorizontal } from 'lucide-react'
import { taskService } from '../services/taskService'
import { useDebounce } from '../hooks/useDebounce'
import { useDataRefresh } from '../hooks/useDataRefresh'
import { getErrorMessage } from '../utils/errors'
import { Button, Pagination, Select } from '../components/ui'
import TaskList from '../components/TaskList'
import TaskForm from '../components/TaskForm'
import { useToast } from '../hooks/useToast'

const PAGE_SIZE = 10

export default function Tasks() {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState(null)
  const [search, setSearch] = useState('')
  const [priority, setPriority] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [order, setOrder] = useState('desc')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [createOpen, setCreateOpen] = useState(params.get('new') === '1')
  const toast = useToast()
  const query = useDebounce(search)
  const status = params.get('status') || 'all'
  const page = Number(params.get('page') || 1)
  const setFilter = (key, value) => {
    const next = new URLSearchParams(params)
    if (value && value !== 'all') next.set(key, value)
    else next.delete(key)
    next.delete('page')
    setParams(next, { replace: true })
  }
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      setData(await taskService.list({ search: query || undefined, status, priority: priority || undefined, sort_by: sortBy, order, page, page_size: PAGE_SIZE }))
    } catch (err) { setError(getErrorMessage(err, 'Could not load tasks.')) }
    finally { setLoading(false) }
  }, [query, status, priority, sortBy, order, page])
  useEffect(() => { load() }, [load])
  useDataRefresh(load)
  const create = async (values) => {
    await taskService.create(values)
    setCreateOpen(false)
    if (params.has('new')) {
      const next = new URLSearchParams(params)
      next.delete('new')
      setParams(next, { replace: true })
    }
    toast('Task created')
    await load()
  }
  return <div className="page-stack">
    <section className="page-title-row"><div><span className="eyebrow">YOUR WORKSPACE</span><h1>My tasks</h1><p>Keep the important things moving.</p></div><Button onClick={() => setCreateOpen(true)}><Plus size={17} /> New task</Button></section>
    <section className="panel">
      <div className="task-toolbar"><div className="search-box grow"><Search size={17} /><input aria-label="Search tasks by title" placeholder="Search by title…" value={search} onChange={(event) => { setSearch(event.target.value); if (page !== 1) setFilter('page', '') }} /></div><div className="toolbar-filters"><Select label="Priority" value={priority} onChange={(event) => { setPriority(event.target.value); if (page !== 1) setFilter('page', '') }}><option value="">Any priority</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></Select><Select label="Sort by" value={sortBy} onChange={(event) => setSortBy(event.target.value)}><option value="created_at">Created date</option><option value="due_date">Due date</option><option value="priority">Priority</option></Select><Select label="Order" value={order} onChange={(event) => setOrder(event.target.value)}><option value="desc">Newest / descending</option><option value="asc">Oldest / ascending</option></Select></div></div>
      <div className="filter-row"><div className="tabs" aria-label="Task status">{['all', 'pending', 'completed'].map((item) => <button key={item} className={status === item ? 'selected' : ''} onClick={() => setFilter('status', item)}>{item[0].toUpperCase() + item.slice(1)}</button>)}</div><span className="results-count"><SlidersHorizontal size={15} /> {data?.total ?? 0} tasks</span></div>
      <TaskList tasks={data?.items} loading={loading} error={error} retry={load} onRefresh={load} emptyTitle="No tasks found" emptyText="Try changing your filters, or add a new task." />
      <Pagination page={data?.page || page} pages={data?.pages || 0} total={data?.total || 0} pageSize={data?.page_size || PAGE_SIZE} onChange={(next) => setFilter('page', String(next))} />
    </section>
    <TaskForm open={createOpen} onClose={() => { setCreateOpen(false); if (params.has('new')) { const next = new URLSearchParams(params); next.delete('new'); setParams(next, { replace: true }) } }} onSubmit={create} />
  </div>
}
