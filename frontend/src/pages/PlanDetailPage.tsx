import { useState, useEffect, FormEvent } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { apiFetch, ApiError } from '../utils/api'
import { LoadingSpinner } from '../components/LoadingSpinner'
import type { PlanWithDetails, PlanUpdate, PlanStatus } from '../types/plan'
import { PLAN_STATUS_CONFIG, PROCESSING_STATUS_CONFIG } from '../types/plan'

function PlanStatusBadge({ status }: { status: PlanStatus }) {
  const config = PLAN_STATUS_CONFIG[status]
  return (
    <span
      className="status-badge"
      style={{
        color: config.color,
        backgroundColor: config.bgColor,
      }}
    >
      {config.label}
    </span>
  )
}

function ProcessingStatusIndicator({
  status,
  error,
}: {
  status: string | null
  error: string | null
}) {
  if (!status) return null

  const config = PROCESSING_STATUS_CONFIG[status as keyof typeof PROCESSING_STATUS_CONFIG]
  if (!config) return null

  return (
    <span
      className="processing-badge"
      style={{
        color: config.color,
        backgroundColor: config.bgColor,
      }}
      title={error || undefined}
    >
      {status === 'generating' && <span className="processing-spinner" />}
      {config.label}
    </span>
  )
}

interface DeleteModalProps {
  isOpen: boolean
  planTitle: string
  onClose: () => void
  onConfirm: () => void
  isDeleting: boolean
}

function DeleteConfirmModal({
  isOpen,
  planTitle,
  onClose,
  onConfirm,
  isDeleting,
}: DeleteModalProps) {
  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-danger" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Delete Plan</h3>
          <button
            className="modal-close-btn"
            onClick={onClose}
            disabled={isDeleting}
            aria-label="Close"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
        <div className="modal-body">
          <div className="delete-warning">
            <svg className="warning-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <p>
              Are you sure you want to delete <strong>"{planTitle}"</strong>? This action cannot be
              undone. All associated tasks and reviews will also be deleted.
            </p>
          </div>
          <div className="modal-actions">
            <button className="btn btn-secondary" onClick={onClose} disabled={isDeleting}>
              Cancel
            </button>
            <button className="btn btn-danger" onClick={onConfirm} disabled={isDeleting}>
              {isDeleting ? 'Deleting...' : 'Delete Plan'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function PlanDetailPage() {
  const { projectId, planId } = useParams<{ projectId: string; planId: string }>()
  const navigate = useNavigate()

  const [plan, setPlan] = useState<PlanWithDetails | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editContent, setEditContent] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  // Delete modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  const fetchPlan = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const data = await apiFetch<PlanWithDetails>(`/plans/${planId}`)
      setPlan(data)
      setEditTitle(data.title)
      setEditContent(data.content || '')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load plan')
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (planId) {
      fetchPlan()
    }
  }, [planId])

  const handleEdit = () => {
    if (plan) {
      setEditTitle(plan.title)
      setEditContent(plan.content || '')
      setIsEditing(true)
      setSaveError(null)
    }
  }

  const handleCancelEdit = () => {
    if (plan) {
      setEditTitle(plan.title)
      setEditContent(plan.content || '')
    }
    setIsEditing(false)
    setSaveError(null)
  }

  const handleSave = async (e: FormEvent) => {
    e.preventDefault()
    if (!plan) return

    setIsSaving(true)
    setSaveError(null)

    try {
      const updateData: PlanUpdate = {}

      // Only include changed fields
      if (editTitle.trim() !== plan.title) {
        updateData.title = editTitle.trim()
      }
      const newContent = editContent.trim() || null
      if (newContent !== plan.content) {
        updateData.content = newContent
      }

      // Skip if nothing changed
      if (Object.keys(updateData).length === 0) {
        setIsEditing(false)
        return
      }

      const updatedPlan = await apiFetch<PlanWithDetails>(`/plans/${planId}`, {
        method: 'PATCH',
        body: JSON.stringify(updateData),
      })

      setPlan(updatedPlan)
      setIsEditing(false)
    } catch (err) {
      if (err instanceof ApiError) {
        setSaveError(err.message)
      } else {
        setSaveError('Failed to save changes')
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!planId || !projectId) return

    setIsDeleting(true)

    try {
      await apiFetch(`/plans/${planId}`, {
        method: 'DELETE',
      })

      // Navigate back to plans list
      navigate(`/projects/${projectId}/plans`)
    } catch (err) {
      setIsDeleting(false)
      setShowDeleteModal(false)
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to delete plan')
      }
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (!projectId || !planId) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>Invalid plan URL</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="page-content">
        <LoadingSpinner message="Loading plan..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={fetchPlan}>
            Try Again
          </button>
        </div>
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>Plan not found</p>
          <Link to={`/projects/${projectId}/plans`} className="btn btn-secondary">
            Back to Plans
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page-content">
      {/* Header */}
      <div className="plan-detail-header">
        <div className="plan-title-section">
          <svg
            className="plan-icon-large"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <div>
            {isEditing ? (
              <input
                type="text"
                className="plan-title-input"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                placeholder="Plan title"
                required
              />
            ) : (
              <h2>{plan.title}</h2>
            )}
            <div className="plan-badges-row">
              <PlanStatusBadge status={plan.status} />
              <ProcessingStatusIndicator
                status={plan.processing_status}
                error={plan.processing_error}
              />
              <span className="plan-version">v{plan.version}</span>
            </div>
          </div>
        </div>
        <div className="plan-actions">
          {isEditing ? (
            <>
              <button className="btn btn-secondary" onClick={handleCancelEdit} disabled={isSaving}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleSave} disabled={isSaving}>
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </>
          ) : (
            <>
              <button className="btn btn-secondary" onClick={handleEdit}>
                <svg
                  className="btn-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                  <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                </svg>
                Edit
              </button>
              <button className="btn btn-danger" onClick={() => setShowDeleteModal(true)}>
                <svg
                  className="btn-icon"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="3 6 5 6 21 6" />
                  <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2" />
                </svg>
                Delete
              </button>
            </>
          )}
        </div>
      </div>

      {saveError && <div className="error-message">{saveError}</div>}

      {/* Content Section */}
      <div className="detail-section">
        <div className="section-header">
          <h3>Plan Content</h3>
        </div>
        {isEditing ? (
          <form onSubmit={handleSave}>
            <div className="form-group">
              <textarea
                className="plan-content-textarea"
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                placeholder="Enter plan content or description..."
                rows={12}
              />
              <span className="form-hint">
                Use markdown formatting. This content describes the plan's scope and requirements.
              </span>
            </div>
          </form>
        ) : plan.content ? (
          <div className="plan-content">
            <pre className="plan-content-pre">{plan.content}</pre>
          </div>
        ) : (
          <div className="plan-content-empty">
            <p>No content yet. Edit this plan to add content, or generate it using AI.</p>
          </div>
        )}
      </div>

      {/* Metadata Section */}
      <div className="detail-section">
        <h3>Details</h3>
        <div className="detail-grid">
          <div className="detail-item">
            <span className="detail-label">Created</span>
            <span className="detail-value">{formatDate(plan.created_at)}</span>
          </div>
          {plan.updated_at && (
            <div className="detail-item">
              <span className="detail-label">Last Updated</span>
              <span className="detail-value">{formatDate(plan.updated_at)}</span>
            </div>
          )}
          <div className="detail-item">
            <span className="detail-label">Version</span>
            <span className="detail-value">{plan.version}</span>
          </div>
          {plan.parent_task_id && (
            <div className="detail-item">
              <span className="detail-label">Parent Task</span>
              <span className="detail-value">
                <Link to={`/projects/${projectId}/tasks/${plan.parent_task_id}`}>
                  View Parent Task
                </Link>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Tasks Section */}
      {plan.tasks.length > 0 && (
        <div className="detail-section">
          <div className="section-header">
            <h3>Spawned Tasks ({plan.tasks.length})</h3>
          </div>
          <div className="task-list-compact">
            {plan.tasks.map((task) => (
              <Link
                key={task.id}
                to={`/projects/${projectId}/tasks/${task.id}`}
                className="task-list-item"
              >
                <span className="task-list-title">{task.title}</span>
                <span
                  className="status-badge"
                  style={{
                    color: PLAN_STATUS_CONFIG[task.status].color,
                    backgroundColor: PLAN_STATUS_CONFIG[task.status].bgColor,
                  }}
                >
                  {PLAN_STATUS_CONFIG[task.status].label}
                </span>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Reviews Section */}
      {plan.reviews.length > 0 && (
        <div className="detail-section">
          <div className="section-header">
            <h3>Reviews ({plan.reviews.length})</h3>
          </div>
          <div className="reviews-list">
            {plan.reviews.map((review) => (
              <div key={review.id} className="review-item">
                <span
                  className={`review-decision ${review.decision === 'approved' ? 'review-approved' : 'review-changes'}`}
                >
                  {review.decision === 'approved' ? 'Approved' : 'Changes Requested'}
                </span>
                <span className="review-date">{formatDate(review.created_at)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Comment Threads Section */}
      {plan.threads.length > 0 && (
        <div className="detail-section">
          <div className="section-header">
            <h3>Comment Threads ({plan.threads.length})</h3>
          </div>
          <div className="threads-list">
            {plan.threads.map((thread) => (
              <div key={thread.id} className="thread-item">
                <span className={`thread-status thread-status-${thread.status}`}>
                  {thread.status}
                </span>
                <span className="thread-comments">{thread.comment_count} comments</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <DeleteConfirmModal
        isOpen={showDeleteModal}
        planTitle={plan.title}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDelete}
        isDeleting={isDeleting}
      />
    </div>
  )
}
