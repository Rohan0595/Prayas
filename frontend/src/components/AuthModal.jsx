import { useState } from 'react'
import { login, register } from '../services/api'

export default function AuthModal({ onAuthSuccess }) {
  const [isLogin, setIsLogin] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    try {
      if (isLogin) {
        const data = await login(email, password)
        localStorage.setItem('omni_token', data.access_token)
        localStorage.setItem('omni_user_email', data.email)
        onAuthSuccess(data)
      } else {
        if (password !== confirmPassword) {
            throw new Error('Passwords do not match')
        }
        const data = await register(email, password)
        setSuccessMsg(data.message)
        setIsLogin(true) // switch to login pane
        setConfirmPassword('') // clear confirmation field
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-overlay">
      <div className="auth-glow-backdrop"></div>
      <div className="auth-modal-card">
        <div className="auth-header">
          <h1 className="auth-title">
            Make your work <br /> successful fast
          </h1>
          <p className="auth-subtitle">
            Sign up for Prayāsa today & start doing your best work
          </p>
        </div>

        <div className="auth-divider">
          <span>or sign {isLogin ? 'in' : 'up'} with email</span>
        </div>

        <form onSubmit={handleSubmit} className="auth-form新">
          <div className="auth-field">
            <label>Email</label>
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          
          <div className="auth-field">
            <label>Password</label>
            <input
              type="password"
              placeholder="Password (min. 6 character)"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
            />
          </div>

          {!isLogin && (
            <div className="auth-field">
              <label>Confirm Password</label>
              <input
                type="password"
                placeholder="Confirm Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>
          )}

          {error && <div className="upload-status error" style={{ textAlign: 'center' }}>{error}</div>}
          {successMsg && <div className="upload-status success" style={{ textAlign: 'center' }}>{successMsg}</div>}

          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Sign Up')}
          </button>
        </form>

        <div className="auth-bottom-switch">
          <span>//////////////////////</span>
          <p>
            {isLogin ? "Don't have an account? " : "Already joined? "}
            <button 
              className="auth-switch-link" 
              onClick={() => { 
                setIsLogin(!isLogin); 
                setError(null); 
                setSuccessMsg(null); 
                setConfirmPassword(''); 
              }}
            >
              {isLogin ? 'Sign up now' : 'Login now'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
