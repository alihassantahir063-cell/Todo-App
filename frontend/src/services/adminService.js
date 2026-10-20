import { api } from './api'

export const adminService = {
  dashboard: () => api.get('/admin/dashboard').then((r) => r.data),
  users: (params) => api.get('/admin/users', { params }).then((r) => r.data),
  user: (id) => api.get(`/admin/users/${id}`).then((r) => r.data),
  setUserStatus: (id, is_active) => api.patch(`/admin/users/${id}/status`, { is_active }).then((r) => r.data),
  tasks: (params) => api.get('/admin/tasks', { params }).then((r) => r.data),
  deleteTask: (id) => api.delete(`/admin/tasks/${id}`),
}
