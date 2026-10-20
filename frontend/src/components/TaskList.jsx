import { useEffect, useState } from 'react'
import { taskService } from '../services/taskService'
import { getErrorMessage } from '../utils/errors'
import { useToast } from '../hooks/useToast'
import TaskItem from './TaskItem'
import TaskForm from './TaskForm'
import { Button, ConfirmDialog, EmptyState, Skeleton } from './ui'
import { ClipboardList, Plus } from 'lucide-react'

export default function TaskList({ tasks = [], loading = false, error, retry, onRefresh, emptyTitle = 'Nothing here yet', emptyText = 'Add a task to get started.' }) {
  const toast = useToast()
  const [visibleTasks, setVisibleTasks] = useState(tasks)
  const [editing, setEditing] = useState(null)
  const [creating, setCreating] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [busyId, setBusyId] = useState(null)
  useEffect(() => setVisibleTasks(tasks), [tasks])
  const save = async (values) => {
    if (editing) await taskService.update(editing.id, values)
    else await taskService.create(values)
    toast(editing ? 'Task updated' : 'Task created')
    setEditing(null); setCreating(false); await onRefresh()
  }
  const toggle = async (task) => {
    const previous = task
    const optimistic = { ...task, status: task.status === 'completed' ? 'pending' : 'completed' }
    setVisibleTasks((current) => current.map((item) => item.id === task.id ? optimistic : item))
    setBusyId(task.id)
    try {
      const updated = await taskService.toggle(task.id)
      setVisibleTasks((current) => current.map((item) => item.id === task.id ? updated : item))
      await onRefresh()
    }
    catch (err) {
      setVisibleTasks((current) => current.map((item) => item.id === task.id ? previous : item))
      toast(getErrorMessage(err), 'error')
    }
    finally { setBusyId(null) }
  }
  const remove = async () => {
    try { await taskService.remove(deleting.id); toast('Task deleted'); setDeleting(null); await onRefresh() }
    catch (err) { toast(getErrorMessage(err), 'error') }
  }
  return <>
    {error && <div className="error-banner" role="alert"><span>{error}</span><Button variant="secondary" onClick={retry}>Retry</Button></div>}
    {loading ? <div className="task-list">{[1, 2, 3].map((n) => <Skeleton className="task-skeleton" key={n} />)}</div>
      : visibleTasks.length ? <div className="task-list">{visibleTasks.map((task) => <TaskItem key={task.id} task={task} onToggle={toggle} onEdit={(item) => setEditing(item)} onDelete={setDeleting} busy={busyId === task.id} />)}</div>
        : <EmptyState title={emptyTitle} description={emptyText} action={<Button onClick={() => setCreating(true)}><Plus size={17} /> Add a task</Button>} />}
    <TaskForm open={creating || Boolean(editing)} task={editing} onClose={() => { setCreating(false); setEditing(null) }} onSubmit={save} />
    <ConfirmDialog open={Boolean(deleting)} title="Delete this task?" description={`“${deleting?.title}” will be permanently deleted.`} confirmLabel="Delete task" danger onClose={() => setDeleting(null)} onConfirm={remove} />
    {!loading && !tasks.length && <span className="sr-only"><ClipboardList /></span>}
  </>
}
