import { useState } from 'react'
import { ArrowLeft, ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { Button, Input } from '../components/ui'
import { authService } from '../services/authService'
import { getErrorMessage } from '../utils/errors'

export default function ForgotPassword() {
  const [message, setMessage] = useState('')
  const [serverError, setServerError] = useState('')
  const [useRecoveryCode, setUseRecoveryCode] = useState(false)
  const [resetComplete, setResetComplete] = useState(false)
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm()

  const submit = async (values) => {
    setMessage('')
    setServerError('')
    try {
      if (useRecoveryCode) {
        await authService.resetWithRecoveryCode({
          email: values.email.trim().toLowerCase(),
          recovery_code: values.recovery_code.trim(),
          new_password: values.password,
        })
        setResetComplete(true)
      } else {
        const response = await authService.requestPasswordReset({
          email: values.email.trim().toLowerCase(),
        })
        setMessage(response.message)
      }
    } catch (error) {
      setServerError(getErrorMessage(
        error,
        useRecoveryCode ? 'Unable to reset your password. Check your email and recovery code.' : 'Unable to send reset instructions. Please try again.',
      ))
    }
  }

  if (resetComplete) {
    return <div className="auth-card-wrap">
      <span className="eyebrow">PASSWORD UPDATED</span>
      <h2>You’re all set</h2>
      <p className="auth-description">Your password has been changed. Sign in with your new password.</p>
      <Button className="auth-submit" onClick={() => window.location.assign('/login')}>
        Back to sign in <ArrowRight size={17} />
      </Button>
    </div>
  }

  return <div className="auth-card-wrap">
    <span className="eyebrow">ACCOUNT RECOVERY</span>
    <h2>Forgot password?</h2>
    <p className="auth-description">{useRecoveryCode
      ? 'Enter your account email, the one-time recovery code you saved in your profile, and a new password.'
      : 'Enter your account email and we’ll send a password reset link if it matches an active account.'}</p>
    <form className="form-stack auth-form" onSubmit={handleSubmit(submit)}>
      <Input
        label="Email address"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        error={errors.email?.message}
        {...register('email', { required: 'Enter your email' })}
      />
      {useRecoveryCode && <>
        <Input
          label="Recovery code"
          autoComplete="off"
          error={errors.recovery_code?.message}
          {...register('recovery_code', { required: 'Enter your recovery code' })}
        />
        <Input
          label="New password"
          type="password"
          autoComplete="new-password"
          error={errors.password?.message}
          {...register('password', {
            required: 'Enter a new password',
            minLength: { value: 8, message: 'Use at least 8 characters' },
            pattern: { value: /^(?=.*[A-Za-z])(?=.*\d).+$/, message: 'Include at least one letter and one number' },
          })}
        />
        <Input
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          error={errors.confirmPassword?.message}
          {...register('confirmPassword', {
            required: 'Confirm your new password',
            validate: (value) => value === watch('password') || 'Passwords do not match',
          })}
        />
      </>}
      {serverError && <p className="form-error" role="alert">{serverError}</p>}
      {message && <p className="auth-status" role="status">{message}</p>}
      <Button type="submit" className="auth-submit" disabled={isSubmitting}>
        {isSubmitting ? (useRecoveryCode ? 'Updating…' : 'Sending…') : <>{useRecoveryCode ? 'Reset password' : 'Send reset link'} <ArrowRight size={17} /></>}
      </Button>
    </form>
    <p className="auth-switch">
      <button type="button" className="auth-text-button" onClick={() => { setUseRecoveryCode(!useRecoveryCode); setServerError(''); setMessage('') }}>
        {useRecoveryCode ? 'Use email reset link instead' : 'Have a recovery code? Use it instead'}
      </button>
    </p>
    <p className="auth-switch"><Link to="/login"><ArrowLeft size={14} /> Back to sign in</Link></p>
  </div>
}
