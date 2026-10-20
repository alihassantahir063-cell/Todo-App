import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { FullPageLoader } from './components/ui'
import { ProtectedRoute, AdminRoute, PublicOnlyRoute } from './routes/Guards'
import AuthLayout from './layouts/AuthLayout'
import UserLayout from './layouts/UserLayout'
import AdminLayout from './layouts/AdminLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Tasks from './pages/Tasks'
import Profile from './pages/Profile'
import AdminDashboard from './pages/AdminDashboard'
import AdminUsers from './pages/AdminUsers'
import AdminTasks from './pages/AdminTasks'
import { AccessDenied, NotFound } from './pages/Errors'

export default function App() {
  const { loading } = useAuth()
  if (loading) return <FullPageLoader label="Restoring your session…" />

  return (
    <Routes>
      <Route element={<PublicOnlyRoute />}>
        <Route element={<AuthLayout />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>
      </Route>
      <Route element={<ProtectedRoute />}>
        <Route element={<UserLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route element={<AdminRoute />}>
          <Route element={<AdminLayout />}>
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/tasks" element={<AdminTasks />} />
          </Route>
        </Route>
      </Route>
      <Route path="/403" element={<AccessDenied />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
