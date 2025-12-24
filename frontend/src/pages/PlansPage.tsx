import { useState, useEffect, useCallback, FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { apiFetch, ApiError } from '../utils/api'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { PlanDetailView } from '../components/PlanDetailView'
import type { PaginatedResponse } from '../types/project'
import {
  Plan,
  PlanWithDetails,
  PlanStatus,
  PlanCreate,
  ProcessingStatus,
  PLAN_STATUS_OPTIONS,
  PLAN_STATUS_CONFIG,
  PROCESSING_STATUS_CONFIG,
} from '../types/plan'
import './PlansPage.css'

interface CreatePlanModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: (plan: Plan) => void
  projectId: string
}

function CreatePlanModal({ isOpen, onClose, onCreated, projectId }: CreatePlanModalProps) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const planData: PlanCreate = {
        title: title.trim(),
        content: content.trim() || null,
      }

      const newPlan = await apiFetch<Plan>(`/projects/${projectId}/plans`, {
        method: 'POST',
        body: JSON.stringify(planData),
      })

      onCreated(newPlan)
      // Reset form
      setTitle('')
      setContent('')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to create plan')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      setError(null)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create New Plan</h3>
          <button
            className="modal-close-btn"
            onClick={handleClose}
            disabled={isSubmitting}
            aria-label="Close"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="plan-title">Plan Title</label>
            <input
              id="plan-title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., Implement user authentication"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="plan-content">Description / Context (Optional)</label>
            <textarea
              id="plan-content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Provide additional context or requirements for this plan..."
              rows={4}
              disabled={isSubmitting}
            />
            <span className="form-hint">
              This context will help when generating the plan content with AI
            </span>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Plan'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

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
  status: ProcessingStatus | null
  error: string | null
}) {
  if (!status) return null

  const config = PROCESSING_STATUS_CONFIG[status]
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
      {status === ProcessingStatus.GENERATING && <span className="processing-spinner" />}
      {config.label}
    </span>
  )
}

export function PlansPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [plans, setPlans] = useState<Plan[]>([])
  const [selectedPlan, setSelectedPlan] = useState<PlanWithDetails | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [statusFilter, setStatusFilter] = useState<PlanStatus | ''>('')

  const fetchPlans = useCallback(async (pageNum: number = 1, status: PlanStatus | '' = '') => {
    if (!projectId) return

    setIsLoading(true)
    setError(null)

    try {
      let url = `/projects/${projectId}/plans?page=${pageNum}&limit=20`
      if (status) {
        url += `&status=${status}`
      }

      const response = await apiFetch<PaginatedResponse<Plan>>(url)
      setPlans(response.items)
      setPage(response.page)
      setTotalPages(response.pages)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load plans')
      }
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (projectId) {
      fetchPlans(1, statusFilter)
    }
  }, [projectId, statusFilter, fetchPlans])

  const fetchPlanDetails = useCallback(async (planId: string) => {
    setIsLoadingDetail(true)

    try {
      const data = await apiFetch<PlanWithDetails>(`/plans/${planId}`)
      setSelectedPlan(data)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load plan details')
      }
    } finally {
      setIsLoadingDetail(false)
    }
  }, [])

  const handlePlanCreated = (newPlan: Plan) => {
    setIsModalOpen(false)
    // Add the new plan to the top of the list
    setPlans((prev) => [newPlan, ...prev])
    // Select the new plan to show its details
    fetchPlanDetails(newPlan.id)
  }

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchPlans(newPage, statusFilter)
    }
  }

  const handleStatusFilterChange = (newStatus: PlanStatus | '') => {
    setStatusFilter(newStatus)
    setPage(1)
  }

  const handlePlanClick = (plan: Plan) => {
    fetchPlanDetails(plan.id)
  }

  const handleClosePlanDetail = () => {
    setSelectedPlan(null)
  }

  const handlePlanUpdated = useCallback(
    (updatedPlan: Plan) => {
      // Update the plan in the list
      setPlans((prev) =>
        prev.map((p) => (p.id === updatedPlan.id ? { ...p, ...updatedPlan } : p))
      )
      // Update the selected plan if it's the same one
      if (selectedPlan?.id === updatedPlan.id) {
        setSelectedPlan((prev) => (prev ? { ...prev, ...updatedPlan } : null))
      }
    },
    [selectedPlan?.id]
  )

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
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

  if (!projectId) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>Project ID is required</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-content plans-page">
      <div className="page-header plans-page__header">
        <div>
          <h2>Plans</h2>
          <p className="page-subtitle">Manage project implementation plans</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <svg
            className="btn-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Plan
        </button>
      </div>

      {/* Status Filter */}
      <div className="filter-bar">
        <div className="form-group filter-group">
          <label htmlFor="status-filter">Filter by Status</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => handleStatusFilterChange(e.target.value as PlanStatus | '')}
          >
            {PLAN_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="error-message plans-page__error">
          {error}
          <button
            className="error-dismiss"
            onClick={() => setError(null)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      )}

      <div className="plans-page__content">
        {/* Plan List */}
        <div className="plans-page__list-section">
          {isLoading ? (
            <LoadingSpinner message="Loading plans..." />
          ) : plans.length === 0 ? (
            <div className="empty-state plans-page__empty">
              <svg
                className="empty-state-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3>{statusFilter ? 'No plans match this filter' : 'No plans yet'}</h3>
              <p>
                {statusFilter
                  ? 'Try a different status filter or create a new plan'
                  : 'Create your first plan to get started'}
              </p>
              <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
                Create Plan
              </button>
            </div>
          ) : (
            <>
              <div className="plans-list">
                {plans.map((plan) => (
                  <div
                    key={plan.id}
                    className={`plan-card ${selectedPlan?.id === plan.id ? 'plan-card--selected' : ''}`}
                    onClick={() => handlePlanClick(plan)}
                  >
                    <div className="plan-card-header">
                      <div className="plan-card-title-row">
                        <svg
                          className="plan-icon"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <h3 className="plan-title">{plan.title}</h3>
                      </div>
                      <div className="plan-badges">
                        <PlanStatusBadge status={plan.status} />
                        <ProcessingStatusIndicator
                          status={plan.processing_status}
                          error={plan.processing_error}
                        />
                      </div>
                    </div>
                    {plan.content && (
                      <div className="plan-card-body">
                        <p className="plan-excerpt">
                          {plan.content.length > 150
                            ? plan.content.substring(0, 150) + '...'
                            : plan.content}
                        </p>
                      </div>
                    )}
                    <div className="plan-card-footer">
                      <span className="plan-meta">
                        v{plan.version} • Created {formatRelativeTime(plan.created_at)}
                        {plan.updated_at && ` • Updated ${formatRelativeTime(plan.updated_at)}`}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {totalPages > 1 && (
                <div className="pagination plans-page__pagination">
                  <button
                    className="pagination-btn btn btn-secondary btn-small"
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page <= 1}
                  >
                    Previous
                  </button>
                  <span className="pagination-info plans-page__page-info">
                    Page {page} of {totalPages}
                  </span>
                  <button
                    className="pagination-btn btn btn-secondary btn-small"
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page >= totalPages}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Plan Detail View */}
        <div className="plans-page__detail-section">
          {isLoadingDetail && <LoadingSpinner message="Loading plan..." />}

          {!isLoadingDetail && selectedPlan && (
            <PlanDetailView
              plan={selectedPlan}
              projectId={projectId}
              onPlanUpdated={handlePlanUpdated}
              onClose={handleClosePlanDetail}
            />
          )}

          {!isLoadingDetail && !selectedPlan && plans.length > 0 && (
            <div className="plans-page__no-selection">
              <div className="plans-page__no-selection-icon">👈</div>
              <p>Select a plan from the list to view details and generate content</p>
            </div>
          )}
        </div>
      </div>

      <CreatePlanModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={handlePlanCreated}
        projectId={projectId}
      />
    </div>
  )
}
