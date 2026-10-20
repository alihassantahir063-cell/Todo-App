import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

export function ProtectedRoute() {
  const { user } = useAuth()
  return user ? <Outlet /> : <Navigate to="/login" replace />
}

export function AdminRoute() {
  const { user } = useAuth()
  return user?.role === 'admin' ? <Outlet /> : <Navigate to="/403" replace />
}

export function PublicOnlyRoute() {
  const { user } = useAuth()
  if (!user) return <Outlet />
  return <Navigate to={user.role === 'admin' ? '/admin' : '/dashboard'} replace />
}
