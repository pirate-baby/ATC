import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../utils/api'
import type {
  ClaudeToken,
  ClaudeTokenCreate,
  TokenValidationResult,
} from '../types/claudeToken'

export function ClaudeTokenSettings() {
  const [token, setToken] = useState<ClaudeToken | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Form state
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [tokenValue, setTokenValue] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [validating, setValidating] = useState(false)

  const fetchToken = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiFetch<ClaudeToken | null>('/claude-tokens/me')
      setToken(data)
    } catch (err) {
      if ((err as { status?: number }).status !== 404) {
        setError('Failed to load token')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchToken()
  }, [fetchToken])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    setSuccess(null)

    try {
      if (token) {
        // Update existing token
        const updates: { name?: string; token?: string } = {}
        if (name && name !== token.name) updates.name = name
        if (tokenValue) updates.token = tokenValue

        await apiFetch<ClaudeToken>('/claude-tokens/me', {
          method: 'PATCH',
          body: JSON.stringify(updates),
        })
        setSuccess('Token updated successfully')
      } else {
        // Create new token
        const payload: ClaudeTokenCreate = { name, token: tokenValue }
        await apiFetch<ClaudeToken>('/claude-tokens', {
          method: 'POST',
          body: JSON.stringify(payload),
        })
        setSuccess('Token added successfully')
      }

      setShowForm(false)
      setTokenValue('')
      await fetchToken()
    } catch (err) {
      setError((err as { message?: string }).message || 'Failed to save token')
    } finally {
      setSubmitting(false)
    }
  }

  const handleValidate = async () => {
    setValidating(true)
    setError(null)
    setSuccess(null)

    try {
      const result = await apiFetch<TokenValidationResult>(
        '/claude-tokens/validate',
        { method: 'POST' }
      )
      if (result.valid) {
        setSuccess('Token is valid and working')
      } else {
        setError(`Token validation failed: ${result.error}`)
      }
      await fetchToken()
    } catch (err) {
      setError((err as { message?: string }).message || 'Validation failed')
    } finally {
      setValidating(false)
    }
  }

  const handleRemove = async () => {
    if (!confirm('Are you sure you want to remove your token from the pool?')) {
      return
    }

    try {
      await apiFetch('/claude-tokens/me', { method: 'DELETE' })
      setToken(null)
      setSuccess('Token removed from pool')
    } catch (err) {
      setError((err as { message?: string }).message || 'Failed to remove token')
    }
  }

  if (loading) {
    return (
      <div className="claude-token-settings">
        <div className="loading-container loading-inline">
          <div className="spinner spinner-medium" />
          <span className="loading-message">Loading token settings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="claude-token-settings">
      <div className="detail-section">
        <h3>Claude Token Pool</h3>

        {/* Instructions */}
        <div className="token-instructions">
          <p>
            Contribute your Claude Pro or Max subscription to power AI features
            for the team. Your token is encrypted and usage is distributed fairly.
          </p>
          <details className="token-setup-guide">
            <summary>How to generate a subscription token</summary>
            <ol>
              <li>Install Claude CLI: <code>npm install -g @anthropic-ai/claude-code</code></li>
              <li>Run: <code>claude setup-token</code></li>
              <li>Follow the prompts to authenticate with your Claude subscription</li>
              <li>Copy the generated token (starts with <code>sk-ant-sid</code>)</li>
              <li>Paste the token below</li>
            </ol>
            <p style={{marginTop: '1rem', padding: '0.5rem', background: '#fff3cd', border: '1px solid #ffc107', borderRadius: '4px'}}>
              <strong>⚠️ Important:</strong> Use subscription tokens (<code>sk-ant-sid</code>) from <code>claude setup-token</code>,
              NOT API keys (<code>sk-ant-api</code>) from console.anthropic.com. API keys will be rejected.
            </p>
          </details>
        </div>

        {error && <div className="error-message">{error}</div>}
        {success && <div className="success-message">{success}</div>}

        {/* Current Token Status */}
        {token && !showForm && (
          <div className="token-status-card">
            <div className="token-status-header">
              <div className="token-info">
                <span className="token-name">{token.name}</span>
                <span className="token-preview">{token.token_preview}</span>
              </div>
              <span className={`status-badge status-${token.status}`}>
                {token.status.replace('_', ' ')}
              </span>
            </div>

            <div className="token-stats">
              <div className="stat-item">
                <span className="stat-label">Requests Served</span>
                <span className="stat-value">{token.request_count}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Last Used</span>
                <span className="stat-value">
                  {token.last_used_at
                    ? new Date(token.last_used_at).toLocaleDateString()
                    : 'Never'}
                </span>
              </div>
              {token.rate_limit_reset_at && (
                <div className="stat-item">
                  <span className="stat-label">Rate Limit Resets</span>
                  <span className="stat-value">
                    {new Date(token.rate_limit_reset_at).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>

            {token.last_error && (
              <div className="token-error">
                <strong>Last Error:</strong> {token.last_error}
              </div>
            )}

            <div className="token-actions">
              <button
                className="btn btn-secondary"
                onClick={() => {
                  setName(token.name)
                  setShowForm(true)
                }}
              >
                Update Token
              </button>
              <button
                className="btn btn-secondary"
                onClick={handleValidate}
                disabled={validating}
              >
                {validating ? 'Validating...' : 'Validate'}
              </button>
              <button
                className="btn btn-danger"
                onClick={handleRemove}
              >
                Remove
              </button>
            </div>
          </div>
        )}

        {/* Add/Edit Form */}
        {(showForm || !token) && (
          <form className="token-form" onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="token-name">Friendly Name</label>
              <input
                type="text"
                id="token-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Personal Account"
                required
              />
              <span className="form-hint">
                A name to identify this token (only visible to you)
              </span>
            </div>

            <div className="form-group">
              <label htmlFor="token-value">
                {token ? 'New Subscription Token (optional)' : 'Claude Subscription Token'}
              </label>
              <input
                type="password"
                id="token-value"
                value={tokenValue}
                onChange={(e) => setTokenValue(e.target.value)}
                placeholder="sk-ant-sid... (from claude setup-token)"
                required={!token}
                autoComplete="off"
              />
              <span className="form-hint">
                Must start with <code>sk-ant-sid</code> (from <code>claude setup-token</code>)
              </span>
            </div>

            <div className="form-actions">
              {token && (
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowForm(false)
                    setTokenValue('')
                  }}
                >
                  Cancel
                </button>
              )}
              <button
                type="submit"
                className="btn btn-primary"
                disabled={submitting}
              >
                {submitting
                  ? 'Saving...'
                  : token
                  ? 'Update Token'
                  : 'Add Token to Pool'}
              </button>
            </div>
          </form>
        )}

        {/* No Token CTA */}
        {!token && !showForm && (
          <div className="empty-state">
            <svg
              className="empty-state-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <h3>No Token Added</h3>
            <p>
              Contribute your Claude subscription to help power AI features for
              the team.
            </p>
            <button
              className="btn btn-primary"
              onClick={() => setShowForm(true)}
            >
              Add Your Token
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
