import { useState } from 'react'
import { KeyRound, Save, UserRound } from 'lucide-react'
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
  const profile = useForm({ defaultValues: { name: user?.name || '', email: user?.email || '' } })
  const password = useForm()
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
      password.reset(); toast('Password changed')
    } catch (error) { setPasswordError(getErrorMessage(error)) }
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
  </div>
}
