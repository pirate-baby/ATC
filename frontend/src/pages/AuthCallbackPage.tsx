import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function AuthCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { handleCallback } = useAuth()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const errorParam = searchParams.get('error')
    const errorDescription = searchParams.get('error_description')

    if (errorParam) {
      setError(errorDescription || errorParam)
      return
    }

    if (!code || !state) {
      setError('Missing OAuth parameters')
      return
    }

    handleCallback(code, state)
      .then(() => {
        navigate('/', { replace: true })
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Authentication failed')
      })
  }, [searchParams, handleCallback, navigate])

  if (error) {
    return (
      <div className="callback-page">
        <div className="callback-container">
          <h2>Authentication Failed</h2>
          <p className="error-message">{error}</p>
          <button onClick={() => navigate('/login', { replace: true })}>
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="callback-page">
      <div className="callback-container">
        <h2>Signing you in...</h2>
        <div className="spinner" />
      </div>
    </div>
  )
}
