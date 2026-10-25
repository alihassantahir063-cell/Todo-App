import { api } from './api'

export const authService = {
  register: (data) => api.post('/auth/register', data).then((r) => r.data),
  login: (data) => api.post('/auth/login', data).then((r) => r.data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get('/auth/me').then((r) => r.data),
  updateProfile: (data) => api.patch('/auth/me', data).then((r) => r.data),
  changePassword: (data) => api.post('/auth/change-password', data),
  requestPasswordReset: (data) => api.post('/auth/forgot-password', data).then((r) => r.data),
  resetPassword: (data) => api.post('/auth/reset-password', data),
  createRecoveryCode: (data) => api.post('/auth/recovery-code', data).then((r) => r.data),
  resetWithRecoveryCode: (data) => api.post('/auth/reset-with-recovery-code', data),
}
