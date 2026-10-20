import { api } from './api'

export const taskService = {
  list: (params) => api.get('/tasks', { params }).then((r) => r.data),
  stats: () => api.get('/tasks/stats').then((r) => r.data),
  get: (id) => api.get(`/tasks/${id}`).then((r) => r.data),
  create: (data) => api.post('/tasks', data).then((r) => r.data),
  update: (id, data) => api.patch(`/tasks/${id}`, data).then((r) => r.data),
  toggle: (id) => api.patch(`/tasks/${id}/toggle`).then((r) => r.data),
  remove: (id) => api.delete(`/tasks/${id}`),
}
