import { ProcessingStatus, ProcessingStatusLabels } from '../types/plan'
import './ProcessingStatusBadge.css'

interface ProcessingStatusBadgeProps {
  status: ProcessingStatus | null
  error?: string | null
  showLabel?: boolean
}

export function ProcessingStatusBadge({
  status,
  error,
  showLabel = true,
}: ProcessingStatusBadgeProps) {
  if (!status) {
    return null
  }

  const statusClass = `processing-badge processing-badge--${status}`
  const label = ProcessingStatusLabels[status]

  return (
    <span className={statusClass} title={error || undefined}>
      {status === ProcessingStatus.GENERATING && (
        <span className="processing-badge__spinner" />
      )}
      {status === ProcessingStatus.FAILED && (
        <span className="processing-badge__icon">!</span>
      )}
      {status === ProcessingStatus.COMPLETED && (
        <span className="processing-badge__icon">✓</span>
      )}
      {showLabel && <span className="processing-badge__label">{label}</span>}
    </span>
  )
}
