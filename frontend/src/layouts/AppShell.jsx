import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { CheckSquare, LayoutDashboard, ListTodo, LogOut, Menu, Moon, Settings, Shield, Sun, Users, X } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { Button } from '../components/ui'
import AIChatWidget from '../components/AIChatWidget'
import ReminderNotifications from '../components/ReminderNotifications'

export default function AppShell({ admin = false, children }) {
  const [drawer, setDrawer] = useState(false)
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const { pathname } = useLocation()
  const links = admin
    ? [{ to: '/admin', label: 'Overview', icon: LayoutDashboard, end: true }, { to: '/admin/users', label: 'Users', icon: Users }, { to: '/admin/tasks', label: 'All tasks', icon: ListTodo }, { to: '/admin/profile', label: 'Profile', icon: Settings }]
    : [{ to: '/dashboard', label: 'Overview', icon: LayoutDashboard }, { to: '/tasks', label: 'My tasks', icon: ListTodo }, { to: '/profile', label: 'Profile', icon: Settings }]
  const initials = user?.name?.split(/\s+/).map((part) => part[0]).slice(0, 2).join('').toUpperCase() || 'U'
  return <div className="app-shell">
    {drawer && <button className="drawer-scrim" aria-label="Close navigation" onClick={() => setDrawer(false)} />}
    <aside className={`sidebar ${drawer ? 'drawer-open' : ''}`}>
      <div className="sidebar-brand"><div className="brand"><span className="brand-mark"><CheckSquare size={20} /></span>daymark</div><button className="icon-button drawer-close" aria-label="Close menu" onClick={() => setDrawer(false)}><X size={20} /></button></div>
      <div className="workspace-label">{admin ? <><Shield size={14} /> ADMIN WORKSPACE</> : 'WORKSPACE'}</div>
      <nav className="side-nav" aria-label="Main navigation">{links.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setDrawer(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}><Icon size={18} /><span>{label}</span>{pathname === to && <span className="nav-indicator" />}</NavLink>)}</nav>
      <div className="sidebar-bottom"><button className="nav-link theme-link" onClick={toggleTheme}>{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}<span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span></button>
        <div className="profile-mini"><span className="avatar">{initials}</span><div className="profile-mini-copy"><strong>{user?.name}</strong><span>{user?.email}</span></div><button className="icon-button" aria-label="Log out" title="Log out" onClick={logout}><LogOut size={17} /></button></div>
      </div>
    </aside>
    <div className="app-main"><header className="topbar"><button className="icon-button mobile-menu" aria-label="Open menu" onClick={() => setDrawer(true)}><Menu size={21} /></button><div className="breadcrumb">{admin ? 'Administration' : 'My workspace'} <span>/</span> <strong>{links.find((link) => pathname === link.to)?.label || (pathname.startsWith('/admin') ? 'Administration' : 'Overview')}</strong></div><div className="topbar-right"><span className="today">{new Date().toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}</span><Button variant="soft" className="topbar-theme" aria-label="Toggle color theme" onClick={toggleTheme}>{theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}</Button></div></header>
      <main className="page-content">{children}</main>
    </div>
    {user && <>
      <ReminderNotifications key={user.id} userId={user.id} />
      <AIChatWidget key={user.id} userId={user.id} />
    </>}
  </div>
}
