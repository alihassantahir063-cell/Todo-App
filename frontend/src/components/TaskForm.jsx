import { useEffect } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { getErrorMessage } from '../utils/errors'
import { Button, Input, Modal, Select } from './ui'

function toLocalDateTimeInput(value) {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return localDate.toISOString().slice(0, 16)
}

function isDueDateReminder(reminderAt, dueDate) {
  if (!reminderAt || !dueDate) return false
  const reminder = new Date(reminderAt)
  const due = new Date(`${String(dueDate).slice(0, 10)}T00:00:00`)
  return reminder.getFullYear() === due.getFullYear()
    && reminder.getMonth() === due.getMonth()
    && reminder.getDate() === due.getDate()
    && reminder.getHours() === 9
    && reminder.getMinutes() === 0
}

export default function TaskForm({ open, task, onClose, onSubmit }) {
  const { control, register, handleSubmit, reset, setError, formState: { errors, isSubmitting } } = useForm({
    defaultValues: { title: '', description: '', priority: 'medium', due_date: '', due_date_reminder: true, custom_reminder_at: '' },
  })
  const dueDate = useWatch({ control, name: 'due_date' })
  useEffect(() => {
    reset({
      title: task?.title || '',
      description: task?.description || '',
      priority: task?.priority || 'medium',
      due_date: task?.due_date ? String(task.due_date).slice(0, 10) : '',
      due_date_reminder: task ? isDueDateReminder(task.reminder_at, task.due_date) : true,
      custom_reminder_at: task?.reminder_at && !isDueDateReminder(task.reminder_at, task.due_date)
        ? toLocalDateTimeInput(task.reminder_at)
        : '',
    })
  }, [task, open, reset])
  const submit = async (values) => {
    const customReminder = values.custom_reminder_at ? new Date(values.custom_reminder_at) : null
    if (customReminder && Number.isNaN(customReminder.getTime())) {
      setError('custom_reminder_at', { message: 'Choose a valid reminder date and time' })
      return
    }
    const dueDateReminder = values.due_date && values.due_date_reminder
      ? new Date(`${values.due_date}T09:00:00`)
      : null
    const reminder = customReminder || dueDateReminder
    const payload = {
      title: values.title,
      description: values.description,
      priority: values.priority,
      due_date: values.due_date || null,
      reminder_at: reminder ? reminder.toISOString() : null,
    }
    try { await onSubmit(payload) } catch (error) {
      setError('root', { message: getErrorMessage(error) })
    }
  }
  return <Modal open={open} onClose={onClose} title={task ? 'Edit task' : 'Create a task'}>
    <form onSubmit={handleSubmit(submit)}>
      <div className="modal-body form-stack">
        <Input label="Task title" placeholder="What needs to get done?" maxLength={200} error={errors.title?.message} {...register('title', { required: 'A title is required', maxLength: { value: 200, message: 'Keep the title to 200 characters or fewer' }, setValueAs: (value) => value.trim() })} />
        <label className="field"><span className="field-label">Description <span className="muted">(optional)</span></span><textarea className="input textarea" rows="4" placeholder="Add a few details…" {...register('description')} /></label>
        <div className="form-grid">
          <Select label="Priority" {...register('priority')}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></Select>
          <Input label="Due date" type="date" {...register('due_date')} />
        </div>
        <label className="reminder-option"><input type="checkbox" disabled={!dueDate} {...register('due_date_reminder')} /><span>Notify me on the due date at 9:00 AM</span></label>
        <Input label="Custom reminder date and time (optional)" type="datetime-local" {...register('custom_reminder_at')} />
        <p className="form-hint">A custom time replaces the due-date reminder. Browser notifications require permission and the app to be open.</p>
        {errors.root && <p className="form-error" role="alert">{errors.root.message}</p>}
      </div>
      <footer className="modal-footer"><Button variant="secondary" onClick={onClose} disabled={isSubmitting}>Cancel</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : task ? 'Save changes' : 'Create task'}</Button></footer>
    </form>
  </Modal>
}
