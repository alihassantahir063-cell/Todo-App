import { api } from './api'

export const authService = {
  register: (data) => api.post('/auth/register', data).then((r) => r.data),
  login: (data) => api.post('/auth/login', data).then((r) => r.data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me').then((r) => r.data),
  updateProfile: (data) => api.patch('/auth/me', data).then((r) => r.data),
  changePassword: (data) => api.post('/auth/change-password', data),
}
