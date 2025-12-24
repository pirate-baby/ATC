import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function DashboardPage() {
  const { user } = useAuth()
  const [health, setHealth] = useState<string>('checking...')

  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    fetch(`${apiUrl}/health`)
      .then((res) => res.json())
      .then((data) => setHealth(data.status))
      .catch(() => setHealth('error'))
  }, [])

  return (
    <div className="page-content">
      <div className="dashboard-welcome">
        <h2>Welcome{user?.display_name ? `, ${user.display_name}` : ''}!</h2>
        <p className="dashboard-subtitle">
          Automated Team Collaboration - Manage your projects and tasks
        </p>
      </div>

      <div className="dashboard-status">
        <span className="status-label">Backend Status:</span>
        <span
          className={`status-value ${health === 'ok' ? 'status-ok' : health === 'error' ? 'status-error' : ''}`}
        >
          {health}
        </span>
      </div>

      <div className="dashboard-actions">
        <Link to="/projects" className="dashboard-action-card">
          <svg
            className="action-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
          </svg>
          <div className="action-text">
            <h3>View Projects</h3>
            <p>Manage your projects and repositories</p>
          </div>
        </Link>
      </div>
    </div>
  )
}
