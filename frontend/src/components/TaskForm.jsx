import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { getErrorMessage } from '../utils/errors'
import { Button, Input, Modal, Select } from './ui'

export default function TaskForm({ open, task, onClose, onSubmit }) {
  const { register, handleSubmit, reset, setError, formState: { errors, isSubmitting } } = useForm({
    defaultValues: { title: '', description: '', priority: 'medium', due_date: '' },
  })
  useEffect(() => {
    reset({
      title: task?.title || '',
      description: task?.description || '',
      priority: task?.priority || 'medium',
      due_date: task?.due_date ? String(task.due_date).slice(0, 10) : '',
    })
  }, [task, open, reset])
  const submit = async (values) => {
    const payload = { ...values, due_date: values.due_date || null }
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
        {errors.root && <p className="form-error" role="alert">{errors.root.message}</p>}
      </div>
      <footer className="modal-footer"><Button variant="secondary" onClick={onClose} disabled={isSubmitting}>Cancel</Button><Button type="submit" disabled={isSubmitting}>{isSubmitting ? 'Saving…' : task ? 'Save changes' : 'Create task'}</Button></footer>
    </form>
  </Modal>
}
