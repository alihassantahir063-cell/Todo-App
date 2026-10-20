import { useCallback, useEffect, useState } from 'react'
import { Search, UserRound, UserRoundCheck, UserRoundX } from 'lucide-react'
import { adminService } from '../services/adminService'
import { useAuth } from '../hooks/useAuth'
import { useDebounce } from '../hooks/useDebounce'
import { useDataRefresh } from '../hooks/useDataRefresh'
import { useToast } from '../hooks/useToast'
import { getErrorMessage } from '../utils/errors'
import { Badge, Button, ConfirmDialog, Modal, Pagination, Select, Skeleton } from '../components/ui'

const PAGE_SIZE = 10

export default function AdminUsers() {
  const { user: currentUser } = useAuth()
  const toast = useToast()
  const [data, setData] = useState(null)
  const [search, setSearch] = useState('')
  const [role, setRole] = useState('')
  const [active, setActive] = useState('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const [pending, setPending] = useState(null)
  const [busy, setBusy] = useState(false)
  const query = useDebounce(search)
  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      setData(await adminService.users({ search: query || undefined, role: role || undefined, is_active: active === '' ? undefined : active === 'true', page, page_size: PAGE_SIZE }))
    } catch (err) { setError(getErrorMessage(err, 'Could not load users.')) }
    finally { setLoading(false) }
  }, [query, role, active, page])
  useEffect(() => { load() }, [load])
  useDataRefresh(load)
  const showDetails = async (person) => {
    try { setSelected(await adminService.user(person.id)) }
    catch (err) { toast(getErrorMessage(err), 'error') }
  }
  const toggleStatus = async () => {
    setBusy(true)
    try {
      await adminService.setUserStatus(pending.id, !pending.is_active)
      toast(pending.is_active ? 'User deactivated' : 'User activated')
      setPending(null); await load()
      if (selected?.id === pending.id) setSelected(await adminService.user(pending.id))
    } catch (err) { toast(getErrorMessage(err), 'error') }
    finally { setBusy(false) }
  }
  const changeFilter = (setter, value) => { setter(value); setPage(1) }
  return <div className="page-stack">
    <section className="page-title-row"><div><span className="eyebrow">PEOPLE</span><h1>Users</h1><p>Manage accounts and access in your workspace.</p></div></section>
    <section className="panel">
      <div className="admin-toolbar"><div className="search-box grow"><Search size={17} /><input aria-label="Search users by name or email" placeholder="Search name or email…" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1) }} /></div><Select label="Role" value={role} onChange={(event) => changeFilter(setRole, event.target.value)}><option value="">All roles</option><option value="user">User</option><option value="admin">Admin</option></Select><Select label="Account status" value={active} onChange={(event) => changeFilter(setActive, event.target.value)}><option value="">Any status</option><option value="true">Active</option><option value="false">Inactive</option></Select></div>
      {error && <div className="error-banner" role="alert">{error}<Button variant="secondary" onClick={load}>Retry</Button></div>}
      {loading ? <div className="table-skeleton">{[1, 2, 3, 4].map((n) => <Skeleton key={n} />)}</div> : <div className="table-scroll"><table className="data-table"><thead><tr><th>User</th><th>Role</th><th>Status</th><th>Joined</th><th>Actions</th></tr></thead><tbody>{(data?.items || []).map((person) => <tr key={person.id}><td><div className="table-user"><span className="avatar">{person.name?.slice(0, 1)?.toUpperCase()}</span><div><strong>{person.name}</strong><span>{person.email}</span></div></div></td><td><Badge tone={person.role === 'admin' ? 'violet' : 'neutral'}>{person.role}</Badge></td><td><Badge tone={person.is_active ? 'success' : 'neutral'}>{person.is_active ? 'Active' : 'Inactive'}</Badge></td><td>{person.created_at ? new Date(person.created_at).toLocaleDateString() : '—'}</td><td><div className="table-actions"><Button variant="secondary" className="small" onClick={() => showDetails(person)}>Details</Button><Button variant={person.is_active ? 'danger-ghost' : 'soft'} className="small" disabled={String(person.id) === String(currentUser?.id)} title={String(person.id) === String(currentUser?.id) ? 'You cannot deactivate yourself' : undefined} onClick={() => setPending(person)}>{person.is_active ? <><UserRoundX size={15} /> Deactivate</> : <><UserRoundCheck size={15} /> Activate</>}</Button></div></td></tr>)}</tbody></table>
        {!data?.items?.length && <div className="empty-inline">No users match these filters.</div>}</div>}
      <Pagination page={data?.page || page} pages={data?.pages || 0} total={data?.total || 0} pageSize={data?.page_size || PAGE_SIZE} onChange={setPage} />
    </section>
    <Modal open={Boolean(selected)} onClose={() => setSelected(null)} title="User details">
      {selected && <div className="detail-body"><div className="detail-person"><span className="avatar large">{selected.name?.slice(0, 1)?.toUpperCase()}</span><div><h3>{selected.name}</h3><p>{selected.email}</p></div></div><div className="detail-grid"><div><span>Role</span><strong>{selected.role}</strong></div><div><span>Status</span><strong>{selected.is_active ? 'Active' : 'Inactive'}</strong></div><div><span>Total tasks</span><strong>{selected.task_count ?? selected.total_tasks ?? selected.tasks_count ?? 0}</strong></div><div><span>Completed tasks</span><strong>{selected.completed_task_count ?? selected.completed_tasks ?? 0}</strong></div><div><span>Joined</span><strong>{selected.created_at ? new Date(selected.created_at).toLocaleDateString() : '—'}</strong></div></div><div className="modal-footer"><Button variant="secondary" onClick={() => setSelected(null)}>Close</Button></div></div>}
    </Modal>
    <ConfirmDialog open={Boolean(pending)} title={`${pending?.is_active ? 'Deactivate' : 'Activate'} this user?`} description={pending?.is_active ? `${pending?.name} will no longer be able to access their account.` : `${pending?.name} will regain access to their account.`} confirmLabel={pending?.is_active ? 'Deactivate user' : 'Activate user'} danger={pending?.is_active} busy={busy} onClose={() => setPending(null)} onConfirm={toggleStatus} />
    <span className="sr-only"><UserRound /></span>
  </div>
}
