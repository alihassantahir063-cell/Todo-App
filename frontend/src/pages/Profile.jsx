import { Bell, KeyRound, Save, UserRound } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { authService } from '../services/authService'
import { useAuth } from '../hooks/useAuth'
import { useToast } from '../hooks/useToast'
import { getErrorMessage } from '../utils/errors'
import { Button, Input } from '../components/ui'

export default function Profile() {
  const { user, refreshUser } = useAuth()
  const toast = useToast()
  const [profileError, setProfileError] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [recoveryError, setRecoveryError] = useState('')
  const [notificationPermission, setNotificationPermission] = useState(
    () => ('Notification' in window ? Notification.permission : 'unsupported'),
  )
  const [notificationError, setNotificationError] = useState('')
  const profile = useForm({ defaultValues: { name: user?.name || '', email: user?.email || '' } })
  const password = useForm()
  const recovery = useForm()
  useEffect(() => {
    const updatePermission = () => {
      setNotificationPermission('Notification' in window ? Notification.permission : 'unsupported')
    }
    window.addEventListener('focus', updatePermission)
    return () => window.removeEventListener('focus', updatePermission)
  }, [])
  const updateProfile = async (values) => {
    setProfileError('')
    try {
      await authService.updateProfile({ name: values.name.trim(), email: values.email.trim().toLowerCase() })
      await refreshUser(); toast('Profile updated')
    } catch (error) { setProfileError(getErrorMessage(error)) }
  }
  const updatePassword = async (values) => {
    setPasswordError('')
    try {
      await authService.changePassword({ current_password: values.current_password, new_password: values.new_password })
      password.reset(); setRecoveryCode(''); toast('Password changed')
    } catch (error) { setPasswordError(getErrorMessage(error)) }
  }
  const createRecoveryCode = async (values) => {
    setRecoveryError('')
    try {
      const response = await authService.createRecoveryCode({ current_password: values.current_password })
      setRecoveryCode(response.recovery_code)
      recovery.reset()
    } catch (error) { setRecoveryError(getErrorMessage(error)) }
  }
  const enableNotifications = async () => {
    setNotificationError('')
    try {
      const permission = await Notification.requestPermission()
      setNotificationPermission(permission)
    } catch (error) {
      console.error('Could not request browser notification permission.', error)
      setNotificationError('Unable to request notification permission in this browser.')
    }
  }
  return <div className="page-stack narrow-page">
    <section className="page-title-row"><div><span className="eyebrow">ACCOUNT SETTINGS</span><h1>Your profile</h1><p>Update your details and keep your account secure.</p></div></section>
    <section className="panel settings-panel"><div className="settings-heading"><span className="settings-icon"><UserRound size={19} /></span><div><h2>Personal details</h2><p>These details are associated with your account.</p></div></div>
      <form className="settings-form" onSubmit={profile.handleSubmit(updateProfile)}>
        <Input label="Name" autoComplete="name" error={profile.formState.errors.name?.message} {...profile.register('name', { required: 'Name is required', maxLength: { value: 100, message: 'Name is too long' } })} />
        <Input label="Email address" type="email" autoComplete="email" error={profile.formState.errors.email?.message} {...profile.register('email', { required: 'Email is required' })} />
        {profileError && <p className="form-error" role="alert">{profileError}</p>}
        <div className="settings-actions"><Button type="submit" disabled={profile.formState.isSubmitting}><Save size={16} /> Save profile</Button></div>
      </form>
    </section>
    <section className="panel settings-panel"><div className="settings-heading"><span className="settings-icon"><KeyRound size={19} /></span><div><h2>Change password</h2><p>Choose a new password you haven’t used before.</p></div></div>
      <form className="settings-form" onSubmit={password.handleSubmit(updatePassword)}>
        <Input label="Current password" type="password" autoComplete="current-password" error={password.formState.errors.current_password?.message} {...password.register('current_password', { required: 'Enter your current password' })} />
        <Input label="New password" type="password" autoComplete="new-password" error={password.formState.errors.new_password?.message} {...password.register('new_password', { required: 'Enter a new password', minLength: { value: 8, message: 'Use at least 8 characters' }, validate: (v) => /[A-Za-z]/.test(v) && /\d/.test(v) || 'Use at least one letter and one number' })} />
        {passwordError && <p className="form-error" role="alert">{passwordError}</p>}
        <div className="settings-actions"><Button type="submit" disabled={password.formState.isSubmitting}><KeyRound size={16} /> Update password</Button></div>
      </form>
    </section>
    <section className="panel settings-panel"><div className="settings-heading"><span className="settings-icon"><KeyRound size={19} /></span><div><h2>Password recovery code</h2><p>Create a one-time code so you can reset your password without email access.</p></div></div>
      <form className="settings-form" onSubmit={recovery.handleSubmit(createRecoveryCode)}>
        <Input label="Current password" type="password" autoComplete="current-password" error={recovery.formState.errors.current_password?.message} {...recovery.register('current_password', { required: 'Enter your current password' })} />
        {recoveryError && <p className="form-error" role="alert">{recoveryError}</p>}
        {recoveryCode && <div className="recovery-code-result" role="status"><strong>Save this code now. It is shown only once:</strong><code>{recoveryCode}</code><span>Creating a new code replaces this one. Keep it somewhere private, such as a password manager.</span></div>}
        <div className="settings-actions"><Button type="submit" disabled={recovery.formState.isSubmitting}><KeyRound size={16} /> {recovery.formState.isSubmitting ? 'Generating…' : 'Generate recovery code'}</Button></div>
      </form>
    </section>
    <section className="panel settings-panel"><div className="settings-heading"><span className="settings-icon"><Bell size={19} /></span><div><h2>Browser notifications</h2><p>Allow Daymark to show task reminders while the app is open.</p></div></div>
      <div className="settings-form">
        {notificationPermission === 'unsupported' && <p className="form-hint">This browser does not support notifications.</p>}
        {notificationPermission === 'granted' && <p className="auth-status" role="status">Browser notifications are enabled.</p>}
        {notificationPermission === 'denied' && <p className="form-hint">Notifications are blocked in browser settings. Allow them for this site, then reload this page.</p>}
        {notificationError && <p className="form-error" role="alert">{notificationError}</p>}
        {notificationPermission !== 'unsupported' && notificationPermission !== 'granted' && notificationPermission !== 'denied' && <div className="settings-actions"><Button onClick={enableNotifications}><Bell size={16} /> Enable notifications</Button></div>}
      </div>
    </section>
  </div>
}
