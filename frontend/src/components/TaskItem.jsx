import { Bell, CalendarDays, Check, Pencil, Trash2 } from 'lucide-react'
import { Badge } from './ui'

export function isOverdue(task) {
  return task.status === 'pending' && task.due_date && new Date(`${String(task.due_date).slice(0, 10)}T23:59:59`) < new Date()
}

export default function TaskItem({ task, onToggle, onEdit, onDelete, busy = false }) {
  const overdue = isOverdue(task)
  return <article className={`task-item ${task.status === 'completed' ? 'is-complete' : ''}`}>
    <button className={`task-check ${task.status === 'completed' ? 'checked' : ''}`} onClick={() => onToggle(task)} aria-label={task.status === 'completed' ? `Reopen ${task.title}` : `Complete ${task.title}`} disabled={busy}>
      {task.status === 'completed' && <Check size={15} />}
    </button>
    <div className="task-copy"><h3>{task.title}</h3>{task.description && <p>{task.description}</p>}<div className="task-meta">
      <Badge tone={`priority-${task.priority}`}>{task.priority}</Badge>
      {task.due_date && <span className={overdue ? 'due-overdue' : ''}><CalendarDays size={14} />{overdue ? 'Overdue · ' : 'Due '}{new Date(`${String(task.due_date).slice(0, 10)}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>}
      {task.reminder_at && <span><Bell size={14} />{new Date(task.reminder_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>}
    </div></div>
    <div className="task-actions"><button className="icon-button" aria-label={`Edit ${task.title}`} onClick={() => onEdit(task)}><Pencil size={17} /></button><button className="icon-button danger-text" aria-label={`Delete ${task.title}`} onClick={() => onDelete(task)}><Trash2 size={17} /></button></div>
  </article>
}
