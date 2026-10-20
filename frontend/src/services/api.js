import axios from 'axios'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

const unauthorizedListeners = new Set()
export const onUnauthorized = (listener) => {
  unauthorizedListeners.add(listener)
  return () => unauthorizedListeners.delete(listener)
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes('/auth/login')
    if (error.response?.status === 401 && !isLoginRequest) {
      unauthorizedListeners.forEach((listener) => listener())
    }
    return Promise.reject(error)
  },
)
