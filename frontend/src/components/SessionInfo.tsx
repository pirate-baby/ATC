import './SessionInfo.css'

interface SessionInfoProps {
  branchName: string | null
  worktreePath: string | null
  startedAt: string | null
  isActive: boolean
}

export function SessionInfo({
  branchName,
  worktreePath,
  startedAt,
  isActive,
}: SessionInfoProps) {
  if (!branchName && !worktreePath && !startedAt) {
    return null
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return formatDate(dateString)
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch (err) {
      // Fallback for browsers that don't support clipboard API
      console.error('Failed to copy to clipboard:', err)
    }
  }

  return (
    <div className="session-info">
      <div className="session-info__header">
        <h3 className="session-info__title">
          <span className="session-info__icon">
            {isActive ? '\u{1F7E2}' : '\u{26AB}'}
          </span>
          Coding Session
        </h3>
        <span
          className={`session-info__status ${isActive ? 'session-info__status--active' : 'session-info__status--ended'}`}
        >
          {isActive ? 'Active' : 'Ended'}
        </span>
      </div>

      <div className="session-info__details">
        {branchName && (
          <div className="session-info__item">
            <span className="session-info__label">Branch</span>
            <div className="session-info__value-row">
              <code className="session-info__code">{branchName}</code>
              <button
                className="session-info__copy-btn"
                onClick={() => copyToClipboard(branchName)}
                title="Copy branch name"
              >
                Copy
              </button>
            </div>
          </div>
        )}

        {worktreePath && (
          <div className="session-info__item">
            <span className="session-info__label">Worktree Path</span>
            <div className="session-info__value-row">
              <code className="session-info__code session-info__code--path">
                {worktreePath}
              </code>
              <button
                className="session-info__copy-btn"
                onClick={() => copyToClipboard(worktreePath)}
                title="Copy worktree path"
              >
                Copy
              </button>
            </div>
          </div>
        )}

        {startedAt && (
          <div className="session-info__item">
            <span className="session-info__label">Started</span>
            <span
              className="session-info__value"
              title={formatDate(startedAt)}
            >
              {formatRelativeTime(startedAt)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
