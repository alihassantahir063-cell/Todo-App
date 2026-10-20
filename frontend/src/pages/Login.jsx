import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { useAuth } from '../hooks/useAuth'
import { getErrorMessage } from '../utils/errors'
import { Button, Input } from '../components/ui'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [show, setShow] = useState(false)
  const [serverError, setServerError] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm()
  const submit = async (values) => {
    setServerError('')
    try {
      const user = await login(values)
      navigate(user.role === 'admin' ? '/admin' : '/dashboard', { replace: true })
    } catch (error) { setServerError(getErrorMessage(error, 'Unable to sign in. Please try again.')) }
  }
  return <div className="auth-card-wrap"><span className="eyebrow">WELCOME BACK</span><h2>Sign in to Daymark</h2><p className="auth-description">Pick up right where you left off.</p>
    <form className="form-stack auth-form" onSubmit={handleSubmit(submit)}>
      <Input label="Email address" type="email" autoComplete="email" placeholder="you@example.com" error={errors.email?.message} {...register('email', { required: 'Enter your email' })} />
      <label className="field"><span className="field-label">Password</span><span className="password-wrap"><input className="input" type={show ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" aria-invalid={Boolean(errors.password)} {...register('password', { required: 'Enter your password' })} /><button type="button" className="password-toggle" aria-label={show ? 'Hide password' : 'Show password'} onClick={() => setShow(!show)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button></span>{errors.password && <span className="field-error">{errors.password.message}</span>}</label>
      {serverError && <p className="form-error" role="alert">{serverError}</p>}
      <Button type="submit" className="auth-submit" disabled={isSubmitting}>{isSubmitting ? 'Signing in…' : <>Sign in <ArrowRight size={17} /></>}</Button>
    </form>
    <p className="auth-switch">New to Daymark? <Link to="/register">Create an account</Link></p>
  </div>
}
