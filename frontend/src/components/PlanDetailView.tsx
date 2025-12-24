import { useState, useCallback } from 'react'
import {
  Plan,
  PlanWithDetails,
  PlanStatus,
  ProcessingStatus,
  SpawnedTaskSummary,
  PLAN_STATUS_CONFIG,
} from '../types/plan'
import { usePlanGeneration } from '../hooks/usePlanGeneration'
import { useSpawnTasks } from '../hooks/useSpawnTasks'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ProcessingStatusBadge } from './ProcessingStatusBadge'
import { GenerateContentButton } from './GenerateContentButton'
import { GenerationProgressIndicator } from './GenerationProgressIndicator'
import {
  SpawnTasksButton,
  SpawnProgressIndicator,
  SpawnedTasksPreview,
} from './SpawnTasksButton'
import './PlanDetailView.css'

interface PlanDetailViewProps {
  plan: PlanWithDetails
  projectId: string
  onPlanUpdated?: (plan: Plan) => void
  onTasksSpawned?: (tasks: SpawnedTaskSummary[]) => void
  onClose?: () => void
}

export function PlanDetailView({
  plan,
  projectId,
  onPlanUpdated,
  onTasksSpawned,
  onClose,
}: PlanDetailViewProps) {
  const [currentPlan, setCurrentPlan] = useState<PlanWithDetails>(plan)
  const [showSpawnedPreview, setShowSpawnedPreview] = useState(false)
  const [newlySpawnedTasks, setNewlySpawnedTasks] = useState<SpawnedTaskSummary[]>([])

  const handleGenerationComplete = useCallback(
    (updatedPlan: Plan) => {
      setCurrentPlan((prev) => ({
        ...prev,
        ...updatedPlan,
      }))
      onPlanUpdated?.(updatedPlan)
    },
    [onPlanUpdated]
  )

  const {
    isGenerating,
    status: generationStatus,
    error: generationError,
    startGeneration,
    reset: resetGeneration,
  } = usePlanGeneration({
    planId: plan.id,
    onComplete: handleGenerationComplete,
    onError: (error) => {
      console.error('Generation failed:', error)
    },
  })

  const handleRetry = useCallback(() => {
    resetGeneration()
    startGeneration()
  }, [resetGeneration, startGeneration])

  // Spawn tasks handling
  const handleSpawnComplete = useCallback(
    (tasks: SpawnedTaskSummary[]) => {
      setNewlySpawnedTasks(tasks)
      setShowSpawnedPreview(true)
      // Update the plan's task count in state
      setCurrentPlan((prev) => ({
        ...prev,
        tasks: [
          ...prev.tasks,
          ...tasks.map((t) => ({ id: t.id, title: t.title, status: 'backlog' as PlanStatus })),
        ],
      }))
      onTasksSpawned?.(tasks)
    },
    [onTasksSpawned]
  )

  const {
    isSpawning,
    status: spawnStatus,
    error: spawnError,
    startSpawn,
    reset: resetSpawn,
  } = useSpawnTasks({
    planId: plan.id,
    onComplete: handleSpawnComplete,
    onError: (error) => {
      console.error('Task spawning failed:', error)
    },
  })

  const handleSpawnRetry = useCallback(() => {
    resetSpawn()
    startSpawn()
  }, [resetSpawn, startSpawn])

  const handleDismissSpawnedPreview = useCallback(() => {
    setShowSpawnedPreview(false)
    setNewlySpawnedTasks([])
  }, [])

  // Check if plan is approved and has content (can spawn tasks)
  const canSpawnTasks =
    currentPlan.status === 'approved' && !!currentPlan.content

  // Check if spawning is in progress
  const isEffectivelySpawning =
    isSpawning ||
    spawnStatus === ProcessingStatus.PENDING ||
    spawnStatus === ProcessingStatus.GENERATING

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getStatusClass = (status: PlanStatus) => {
    switch (status) {
      case 'approved':
      case 'merged':
        return 'status-ok'
      case 'blocked':
      case 'closed':
        return 'status-error'
      case 'review':
        return 'status-warning'
      default:
        return ''
    }
  }

  const getStatusLabel = (status: PlanStatus) => {
    return PLAN_STATUS_CONFIG[status]?.label || status
  }

  // Check if generation is in progress (either from hook or plan's processing_status)
  const effectiveGenerationStatus =
    generationStatus ||
    (currentPlan.processing_status &&
    currentPlan.processing_status !== ProcessingStatus.COMPLETED
      ? currentPlan.processing_status
      : null)

  const isEffectivelyGenerating =
    isGenerating ||
    effectiveGenerationStatus === ProcessingStatus.PENDING ||
    effectiveGenerationStatus === ProcessingStatus.GENERATING

  return (
    <div className="plan-detail">
      <div className="plan-detail__header">
        <div className="plan-detail__title-section">
          <h2 className="plan-detail__title">{currentPlan.title}</h2>
          <div className="plan-detail__badges">
            <span
              className={`plan-detail__status ${getStatusClass(currentPlan.status)}`}
            >
              {getStatusLabel(currentPlan.status)}
            </span>
            {currentPlan.processing_status && (
              <ProcessingStatusBadge
                status={currentPlan.processing_status}
                error={currentPlan.processing_error}
              />
            )}
          </div>
        </div>

        <div className="plan-detail__actions">
          <GenerateContentButton
            onGenerate={startGeneration}
            isGenerating={isEffectivelyGenerating}
            status={effectiveGenerationStatus}
            hasContent={!!currentPlan.content}
          />
          {canSpawnTasks && (
            <SpawnTasksButton
              onSpawn={startSpawn}
              isSpawning={isEffectivelySpawning}
              status={spawnStatus}
              hasTasks={currentPlan.tasks.length > 0}
            />
          )}
          {onClose && (
            <button className="btn-secondary" onClick={onClose}>
              Close
            </button>
          )}
        </div>
      </div>

      <div className="plan-detail__meta">
        <div className="plan-detail__meta-item">
          <span className="plan-detail__meta-label">Created</span>
          <span className="plan-detail__meta-value">
            {formatDate(currentPlan.created_at)}
          </span>
        </div>
        {currentPlan.updated_at && (
          <div className="plan-detail__meta-item">
            <span className="plan-detail__meta-label">Updated</span>
            <span className="plan-detail__meta-value">
              {formatDate(currentPlan.updated_at)}
            </span>
          </div>
        )}
        <div className="plan-detail__meta-item">
          <span className="plan-detail__meta-label">Version</span>
          <span className="plan-detail__meta-value">v{currentPlan.version}</span>
        </div>
      </div>

      {/* Generation Progress Indicator */}
      {isEffectivelyGenerating && (
        <GenerationProgressIndicator
          status={effectiveGenerationStatus}
          error={generationError || currentPlan.processing_error}
          onRetry={handleRetry}
        />
      )}

      {/* Error state when not actively generating */}
      {!isEffectivelyGenerating &&
        generationStatus === ProcessingStatus.FAILED && (
          <GenerationProgressIndicator
            status={ProcessingStatus.FAILED}
            error={generationError}
            onRetry={handleRetry}
          />
        )}

      {/* Spawn Tasks Progress Indicator */}
      {isEffectivelySpawning && (
        <SpawnProgressIndicator
          status={spawnStatus}
          error={spawnError}
          onRetry={handleSpawnRetry}
        />
      )}

      {/* Spawn Tasks Error state */}
      {!isEffectivelySpawning && spawnStatus === ProcessingStatus.FAILED && (
        <SpawnProgressIndicator
          status={ProcessingStatus.FAILED}
          error={spawnError}
          onRetry={handleSpawnRetry}
        />
      )}

      {/* Newly Spawned Tasks Preview */}
      {showSpawnedPreview && newlySpawnedTasks.length > 0 && (
        <SpawnedTasksPreview
          tasks={newlySpawnedTasks}
          projectId={projectId}
          onDismiss={handleDismissSpawnedPreview}
        />
      )}

      {/* Plan Content */}
      <div className="plan-detail__content-section">
        <h3 className="plan-detail__section-title">Plan Content</h3>
        {currentPlan.content ? (
          <div className="plan-detail__content">
            <MarkdownRenderer content={currentPlan.content} />
          </div>
        ) : (
          <div className="plan-detail__empty-content">
            <div className="plan-detail__empty-icon">📝</div>
            <p className="plan-detail__empty-text">
              No content yet. Click "Generate Content" to have Claude create a
              detailed plan.
            </p>
          </div>
        )}
      </div>

      {/* Related Tasks */}
      {currentPlan.tasks.length > 0 && (
        <div className="plan-detail__tasks-section">
          <h3 className="plan-detail__section-title">
            Spawned Tasks ({currentPlan.tasks.length})
          </h3>
          <ul className="plan-detail__task-list">
            {currentPlan.tasks.map((task) => (
              <li key={task.id} className="plan-detail__task-item">
                <span
                  className={`plan-detail__task-status ${getStatusClass(task.status)}`}
                >
                  {getStatusLabel(task.status)}
                </span>
                <span className="plan-detail__task-title">{task.title}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Reviews */}
      {currentPlan.reviews.length > 0 && (
        <div className="plan-detail__reviews-section">
          <h3 className="plan-detail__section-title">
            Reviews ({currentPlan.reviews.length})
          </h3>
          <ul className="plan-detail__review-list">
            {currentPlan.reviews.map((review) => (
              <li key={review.id} className="plan-detail__review-item">
                <span
                  className={`plan-detail__review-decision ${
                    review.decision === 'approved'
                      ? 'decision-approved'
                      : 'decision-changes'
                  }`}
                >
                  {review.decision === 'approved' ? '✓ Approved' : '✗ Changes Requested'}
                </span>
                <span className="plan-detail__review-date">
                  {formatDate(review.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
