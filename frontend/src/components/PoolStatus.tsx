import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../utils/api'
import type { TokenPoolStats, PoolHealth } from '../types/claudeToken'

interface PoolStatusProps {
  compact?: boolean
}

export function PoolStatus({ compact = false }: PoolStatusProps) {
  const [stats, setStats] = useState<TokenPoolStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true)
      const data = await apiFetch<TokenPoolStats>('/claude-tokens/pool/stats')
      setStats(data)
      setError(null)
    } catch (err) {
      setError('Failed to load pool status')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    // Refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [fetchStats])

  if (loading && !stats) {
    return (
      <div className="pool-status">
        <div className="loading-container loading-inline">
          <div className="spinner spinner-small" />
        </div>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="pool-status pool-status-error">
        <span>{error || 'Unable to load pool status'}</span>
      </div>
    )
  }

  const { status, usage_distribution, fairness_score } = stats
  const healthColors: Record<PoolHealth, string> = {
    healthy: '#059669',
    limited: '#d97706',
    exhausted: '#dc2626',
  }

  if (compact) {
    return (
      <div className="pool-status pool-status-compact">
        <div
          className="pool-health-indicator"
          style={{ backgroundColor: healthColors[status.pool_health] }}
          title={`Pool: ${status.pool_health}`}
        />
        <span className="pool-status-text">
          {status.active_tokens} active
          {status.rate_limited_tokens > 0 && (
            <span className="pool-rate-limited">
              {' '}({status.rate_limited_tokens} rate limited)
            </span>
          )}
        </span>
      </div>
    )
  }

  return (
    <div className="pool-status-full">
      <div className="detail-section">
        <h3>Token Pool Status</h3>

        {/* Health Overview */}
        <div className="pool-health-banner" data-health={status.pool_health}>
          <div className="pool-health-content">
            <span
              className="pool-health-dot"
              style={{ backgroundColor: healthColors[status.pool_health] }}
            />
            <span className="pool-health-label">
              Pool is{' '}
              <strong>{status.pool_health}</strong>
            </span>
          </div>
          {status.pool_health === 'exhausted' && (
            <span className="pool-health-cta">
              The pool needs contributors!
            </span>
          )}
          {status.next_available_at && (
            <span className="pool-next-available">
              Next token available:{' '}
              {new Date(status.next_available_at).toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Stats Grid */}
        <div className="pool-stats-grid">
          <div className="pool-stat">
            <span className="pool-stat-value">{status.total_contributors}</span>
            <span className="pool-stat-label">Contributors</span>
          </div>
          <div className="pool-stat">
            <span className="pool-stat-value">{status.active_tokens}</span>
            <span className="pool-stat-label">Active Tokens</span>
          </div>
          <div className="pool-stat">
            <span className="pool-stat-value">{status.rate_limited_tokens}</span>
            <span className="pool-stat-label">Rate Limited</span>
          </div>
          <div className="pool-stat">
            <span className="pool-stat-value">
              {status.total_requests_served.toLocaleString()}
            </span>
            <span className="pool-stat-label">Requests Served</span>
          </div>
        </div>

        {/* Fairness Score */}
        <div className="pool-fairness">
          <div className="pool-fairness-header">
            <span className="pool-fairness-label">Usage Fairness</span>
            <span className="pool-fairness-score">
              {Math.round(fairness_score * 100)}%
            </span>
          </div>
          <div className="pool-fairness-bar">
            <div
              className="pool-fairness-fill"
              style={{ width: `${fairness_score * 100}%` }}
            />
          </div>
          <span className="pool-fairness-hint">
            {fairness_score >= 0.8
              ? 'Usage is well distributed across contributors'
              : fairness_score >= 0.5
              ? 'Usage is moderately distributed'
              : 'Usage is concentrated on few contributors'}
          </span>
        </div>

        {/* Usage Distribution */}
        {usage_distribution.length > 0 && (
          <div className="pool-distribution">
            <h4>Usage Distribution</h4>
            <div className="distribution-bars">
              {usage_distribution.map((bucket) => (
                <div key={bucket.bucket} className="distribution-bar">
                  <span className="distribution-label">{bucket.bucket}</span>
                  <div className="distribution-bar-container">
                    <div
                      className="distribution-bar-fill"
                      style={{
                        width: `${Math.min(
                          100,
                          (bucket.count / status.total_contributors) * 100
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="distribution-count">{bucket.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Invalid Tokens Warning */}
        {status.invalid_tokens > 0 && (
          <div className="pool-warning">
            <svg
              className="warning-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <span>
              {status.invalid_tokens} token{status.invalid_tokens > 1 ? 's' : ''}{' '}
              need attention (invalid or expired)
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
