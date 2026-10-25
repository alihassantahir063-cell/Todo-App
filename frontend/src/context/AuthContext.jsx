import { createContext, useCallback, useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { authService } from '../services/authService'
import { onUnauthorized } from '../services/api'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { pathname } = useLocation()

  const clearUser = useCallback(() => {
    setUser(null)
    if (!['/login', '/register', '/forgot-password', '/reset-password'].includes(pathname)) {
      navigate('/login', { replace: true })
    }
  }, [navigate, pathname])

  useEffect(() => onUnauthorized(clearUser), [clearUser])

  useEffect(() => {
    let active = true
    authService.me()
      .then((data) => { if (active) setUser(data) })
      .catch(() => { if (active) setUser(null) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const login = async (credentials) => {
    const data = await authService.login(credentials)
    const current = data?.user || await authService.me()
    setUser(current)
    return current
  }
  const register = (values) => authService.register(values)
  const logout = async () => {
    try { await authService.logout() } finally {
      setUser(null)
      navigate('/login', { replace: true })
    }
  }
  const refreshUser = async () => {
    const current = await authService.me()
    setUser(current)
    return current
  }
  const value = useMemo(() => ({ user, loading, login, register, logout, refreshUser, setUser }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
