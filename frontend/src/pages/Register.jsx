import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { useAuth } from '../hooks/useAuth'
import { getErrorMessage } from '../utils/errors'
import { Button, Input } from '../components/ui'

export default function Register() {
  const { register: createAccount } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm()
  const submit = async (values) => {
    setServerError('')
    try {
      await createAccount({ name: values.name.trim(), email: values.email.trim().toLowerCase(), password: values.password })
      navigate('/login', { replace: true, state: { notice: 'Your account is ready. Sign in to continue.' } })
    } catch (error) { setServerError(getErrorMessage(error, 'Unable to create your account.')) }
  }
  return <div className="auth-card-wrap"><span className="eyebrow">A FRESH START</span><h2>Create your account</h2><p className="auth-description">A little clarity goes a long way.</p>
    <form className="form-stack auth-form" onSubmit={handleSubmit(submit)}>
      <Input label="Your name" autoComplete="name" placeholder="Alex Morgan" error={errors.name?.message} {...register('name', { required: 'Enter your name', maxLength: { value: 100, message: 'Name is too long' } })} />
      <Input label="Email address" type="email" autoComplete="email" placeholder="you@example.com" error={errors.email?.message} {...register('email', { required: 'Enter your email', pattern: { value: /^\S+@\S+\.\S+$/, message: 'Enter a valid email address' } })} />
      <Input label="Password" type="password" autoComplete="new-password" placeholder="At least 8 characters" error={errors.password?.message} {...register('password', { required: 'Create a password', minLength: { value: 8, message: 'Use at least 8 characters' }, validate: (value) => /[A-Za-z]/.test(value) && /\d/.test(value) || 'Use at least one letter and one number' })} />
      <Input label="Confirm password" type="password" autoComplete="new-password" placeholder="Type it again" error={errors.confirm?.message} {...register('confirm', { required: 'Confirm your password', validate: (value) => value === watch('password') || 'Passwords do not match' })} />
      {serverError && <p className="form-error" role="alert">{serverError}</p>}
      <Button type="submit" className="auth-submit" disabled={isSubmitting}>{isSubmitting ? 'Creating account…' : <>Create account <ArrowRight size={17} /></>}</Button>
    </form>
    <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
  </div>
}
