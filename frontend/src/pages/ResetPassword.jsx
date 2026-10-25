import { useState } from 'react'
import { ArrowLeft, ArrowRight } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { Button, Input } from '../components/ui'
import { authService } from '../services/authService'
import { getErrorMessage } from '../utils/errors'

function getResetToken() {
  return new URLSearchParams(window.location.hash.slice(1)).get('token') || ''
}

export default function ResetPassword() {
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const [hasReset, setHasReset] = useState(false)
  const token = getResetToken()
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm()

  const submit = async (values) => {
    setServerError('')
    try {
      await authService.resetPassword({ token, new_password: values.password })
      window.history.replaceState(null, '', window.location.pathname)
      setHasReset(true)
    } catch (error) {
      setServerError(getErrorMessage(error, 'Unable to reset your password. Request a new link and try again.'))
    }
  }

  if (hasReset) {
    return <div className="auth-card-wrap">
      <span className="eyebrow">PASSWORD UPDATED</span>
      <h2>You’re all set</h2>
      <p className="auth-description">Your password has been changed. Sign in with your new password.</p>
      <Button className="auth-submit" onClick={() => navigate('/login', { replace: true })}>
        Back to sign in <ArrowRight size={17} />
      </Button>
    </div>
  }

  if (!token) {
    return <div className="auth-card-wrap">
      <span className="eyebrow">ACCOUNT RECOVERY</span>
      <h2>Reset link needed</h2>
      <p className="auth-description">This reset link is missing or invalid. Request a new one to continue.</p>
      <Button className="auth-submit" onClick={() => navigate('/forgot-password')}>
        Request a new link <ArrowRight size={17} />
      </Button>
    </div>
  }

  return <div className="auth-card-wrap">
    <span className="eyebrow">ACCOUNT RECOVERY</span>
    <h2>Choose a new password</h2>
    <p className="auth-description">Use at least 8 characters, including a letter and a number.</p>
    <form className="form-stack auth-form" onSubmit={handleSubmit(submit)}>
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
      {serverError && <p className="form-error" role="alert">{serverError}</p>}
      <Button type="submit" className="auth-submit" disabled={isSubmitting}>
        {isSubmitting ? 'Updating…' : <>Update password <ArrowRight size={17} /></>}
      </Button>
    </form>
    <p className="auth-switch"><Link to="/login"><ArrowLeft size={14} /> Back to sign in</Link></p>
  </div>
}
