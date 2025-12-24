import { useState } from 'react'
import { ProcessingStatus, SpawnedTaskSummary } from '../types/plan'
import './SpawnTasksButton.css'

interface SpawnTasksButtonProps {
  onSpawn: () => Promise<void>
  isSpawning: boolean
  status: ProcessingStatus | null
  disabled?: boolean
  hasTasks?: boolean
}

export function SpawnTasksButton({
  onSpawn,
  isSpawning,
  status,
  disabled = false,
  hasTasks = false,
}: SpawnTasksButtonProps) {
  const [showConfirmModal, setShowConfirmModal] = useState(false)

  const handleClick = () => {
    if (hasTasks) {
      // If tasks already exist, show confirmation
      setShowConfirmModal(true)
    } else {
      // Start spawning directly
      handleSpawn()
    }
  }

  const handleSpawn = async () => {
    setShowConfirmModal(false)
    await onSpawn()
  }

  const handleCancel = () => {
    setShowConfirmModal(false)
  }

  const isDisabled = disabled || isSpawning

  const buttonText = isSpawning
    ? 'Spawning Tasks...'
    : hasTasks
      ? 'Respawn Tasks'
      : 'Spawn Tasks'

  return (
    <>
      <button
        className={`spawn-tasks-button ${isSpawning ? 'spawn-tasks-button--spawning' : ''}`}
        onClick={handleClick}
        disabled={isDisabled}
        title={
          status === ProcessingStatus.FAILED
            ? 'Previous spawning failed. Click to retry.'
            : 'Generate tasks from this approved plan'
        }
      >
        {isSpawning && <span className="spawn-tasks-button__spinner" />}
        <span className="spawn-tasks-button__icon">
          {isSpawning ? '' : ''}
        </span>
        <span>{buttonText}</span>
      </button>

      {showConfirmModal && (
        <div className="spawn-modal-overlay" onClick={handleCancel}>
          <div
            className="spawn-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="spawn-modal__title">Respawn Tasks</h3>
            <p className="spawn-modal__warning">
              This plan already has spawned tasks. Spawning again will create
              new tasks without affecting existing ones. Are you sure?
            </p>
            <div className="spawn-modal__actions">
              <button className="btn-secondary" onClick={handleCancel}>
                Cancel
              </button>
              <button className="btn-primary" onClick={handleSpawn}>
                Spawn New Tasks
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

interface SpawnProgressIndicatorProps {
  status: ProcessingStatus | null
  error?: string | null
  onRetry?: () => void
}

export function SpawnProgressIndicator({
  status,
  error,
  onRetry,
}: SpawnProgressIndicatorProps) {
  if (!status || status === ProcessingStatus.COMPLETED) {
    return null
  }

  const isSpawning =
    status === ProcessingStatus.PENDING ||
    status === ProcessingStatus.GENERATING
  const isFailed = status === ProcessingStatus.FAILED

  return (
    <div
      className={`spawn-progress ${isFailed ? 'spawn-progress--failed' : ''}`}
    >
      <div className="spawn-progress__content">
        {isSpawning && (
          <>
            <div className="spawn-progress__spinner">
              <div className="spawn-progress__spinner-ring" />
              <div className="spawn-progress__spinner-icon"></div>
            </div>
            <div className="spawn-progress__text">
              <h4 className="spawn-progress__title">
                {status === ProcessingStatus.PENDING
                  ? 'Starting task generation...'
                  : 'Claude is generating tasks from your plan'}
              </h4>
              <p className="spawn-progress__description">
                {status === ProcessingStatus.PENDING
                  ? 'Queuing your request...'
                  : 'This may take a minute. Claude is analyzing the plan and creating detailed tasks.'}
              </p>
            </div>
          </>
        )}

        {isFailed && (
          <>
            <div className="spawn-progress__error-icon">!</div>
            <div className="spawn-progress__text">
              <h4 className="spawn-progress__title">Task Spawning Failed</h4>
              <p className="spawn-progress__description">
                {error || 'An unexpected error occurred during task generation.'}
              </p>
              {onRetry && (
                <button
                  className="spawn-progress__retry-button"
                  onClick={onRetry}
                >
                  Try Again
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {isSpawning && (
        <div className="spawn-progress__steps">
          <div
            className={`spawn-progress__step ${status === ProcessingStatus.PENDING ? 'spawn-progress__step--active' : 'spawn-progress__step--completed'}`}
          >
            <span className="spawn-progress__step-dot" />
            <span>Queued</span>
          </div>
          <div
            className={`spawn-progress__step ${status === ProcessingStatus.GENERATING ? 'spawn-progress__step--active' : ''}`}
          >
            <span className="spawn-progress__step-dot" />
            <span>Generating Tasks</span>
          </div>
          <div className="spawn-progress__step">
            <span className="spawn-progress__step-dot" />
            <span>Complete</span>
          </div>
        </div>
      )}
    </div>
  )
}

interface SpawnedTasksPreviewProps {
  tasks: SpawnedTaskSummary[]
  onDismiss?: () => void
  projectId: string
}

export function SpawnedTasksPreview({
  tasks,
  onDismiss,
  projectId,
}: SpawnedTasksPreviewProps) {
  if (tasks.length === 0) {
    return null
  }

  // Build a map of task titles for dependency display
  const taskTitleMap = new Map(tasks.map((t) => [t.id, t.title]))

  return (
    <div className="spawned-tasks-preview">
      <div className="spawned-tasks-preview__header">
        <div className="spawned-tasks-preview__icon"></div>
        <div className="spawned-tasks-preview__header-text">
          <h4 className="spawned-tasks-preview__title">
            {tasks.length} Task{tasks.length !== 1 ? 's' : ''} Generated
          </h4>
          <p className="spawned-tasks-preview__subtitle">
            Tasks have been created from your plan
          </p>
        </div>
        {onDismiss && (
          <button
            className="spawned-tasks-preview__dismiss"
            onClick={onDismiss}
            aria-label="Dismiss"
          >
            x
          </button>
        )}
      </div>

      <ul className="spawned-tasks-preview__list">
        {tasks.map((task) => (
          <li key={task.id} className="spawned-tasks-preview__item">
            <div className="spawned-tasks-preview__item-content">
              <a
                href={`/projects/${projectId}/tasks/${task.id}`}
                className="spawned-tasks-preview__item-title"
              >
                {task.title}
              </a>
              {task.description && (
                <p className="spawned-tasks-preview__item-description">
                  {task.description}
                </p>
              )}
              {task.blocked_by.length > 0 && (
                <div className="spawned-tasks-preview__dependencies">
                  <span className="spawned-tasks-preview__dependency-label">
                    Blocked by:
                  </span>
                  {task.blocked_by.map((depId) => (
                    <span
                      key={depId}
                      className="spawned-tasks-preview__dependency"
                    >
                      {taskTitleMap.get(depId) || depId.slice(0, 8)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>

      <div className="spawned-tasks-preview__actions">
        <a
          href={`/projects/${projectId}/tasks`}
          className="btn-primary"
        >
          View All Tasks
        </a>
      </div>
    </div>
  )
}
