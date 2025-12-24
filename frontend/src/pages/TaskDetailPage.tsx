import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { apiFetch, ApiError } from '../utils/api'
import { LoadingSpinner } from '../components/LoadingSpinner'
import {
  TaskWithDetails,
  TaskStatus,
  TASK_STATUS_CONFIG,
} from '../types/task'
import './TaskDetailPage.css'

function TaskStatusBadge({
  status,
  size = 'normal',
}: {
  status: TaskStatus
  size?: 'normal' | 'large'
}) {
  const config = TASK_STATUS_CONFIG[status]
  return (
    <span
      className={`task-status-badge task-status-badge--${size}`}
      style={{
        color: config.color,
        backgroundColor: config.bgColor,
      }}
      title={config.description}
    >
      {config.label}
    </span>
  )
}

export function TaskDetailPage() {
  const { projectId, taskId } = useParams<{
    projectId: string
    taskId: string
  }>()
  const [task, setTask] = useState<TaskWithDetails | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTask = useCallback(async () => {
    if (!taskId) return

    setIsLoading(true)
    setError(null)

    try {
      const data = await apiFetch<TaskWithDetails>(`/tasks/${taskId}`)
      setTask(data)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load task')
      }
    } finally {
      setIsLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    fetchTask()
  }, [fetchTask])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (!projectId || !taskId) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>Project ID and Task ID are required</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="page-content">
        <LoadingSpinner message="Loading task..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-content">
        <div className="error-state">
          <h3>Error Loading Task</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={fetchTask}>
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!task) {
    return (
      <div className="page-content">
        <div className="error-state">
          <h3>Task Not Found</h3>
          <p>The requested task could not be found.</p>
          <Link to={`/projects/${projectId}/tasks`} className="btn btn-primary">
            Back to Tasks
          </Link>
        </div>
      </div>
    )
  }

  const config = TASK_STATUS_CONFIG[task.status]

  return (
    <div className="page-content task-detail-page">
      {/* Breadcrumb */}
      <nav className="task-detail-page__breadcrumb">
        <Link to={`/projects/${projectId}`}>Project</Link>
        <span className="breadcrumb-separator">/</span>
        <Link to={`/projects/${projectId}/tasks`}>Tasks</Link>
        <span className="breadcrumb-separator">/</span>
        <span className="breadcrumb-current">{task.title}</span>
      </nav>

      {/* Header */}
      <div className="task-detail-page__header">
        <div className="task-detail-page__title-section">
          <h1 className="task-detail-page__title">{task.title}</h1>
          <div className="task-detail-page__badges">
            <TaskStatusBadge status={task.status} size="large" />
            {task.blocked_by.length > 0 && (
              <span className="task-detail-page__blocked-badge">
                Blocked by {task.blocked_by.length} task
                {task.blocked_by.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="task-detail-page__content">
        {/* Main Content */}
        <div className="task-detail-page__main">
          {/* Metadata Card */}
          <div className="task-card-section">
            <div className="task-meta-grid">
              <div className="task-meta-item">
                <span className="task-meta-label">Status</span>
                <span
                  className="task-meta-status"
                  style={{
                    color: config.color,
                    backgroundColor: config.bgColor,
                  }}
                >
                  {config.label}
                </span>
              </div>
              <div className="task-meta-item">
                <span className="task-meta-label">Created</span>
                <span className="task-meta-value">
                  {formatDate(task.created_at)}
                </span>
              </div>
              {task.updated_at && (
                <div className="task-meta-item">
                  <span className="task-meta-label">Updated</span>
                  <span className="task-meta-value">
                    {formatDate(task.updated_at)}
                  </span>
                </div>
              )}
              {task.branch_name && (
                <div className="task-meta-item">
                  <span className="task-meta-label">Git Branch</span>
                  <code className="task-meta-code">{task.branch_name}</code>
                </div>
              )}
              {task.worktree_path && (
                <div className="task-meta-item">
                  <span className="task-meta-label">Worktree</span>
                  <code className="task-meta-code">{task.worktree_path}</code>
                </div>
              )}
            </div>
          </div>

          {/* Description */}
          <div className="task-card-section">
            <h2 className="section-title">Description</h2>
            {task.description ? (
              <div className="task-description">{task.description}</div>
            ) : (
              <p className="task-empty-text">No description provided</p>
            )}
          </div>

          {/* Parent Plan */}
          {task.plan && (
            <div className="task-card-section">
              <h2 className="section-title">Parent Plan</h2>
              <Link
                to={`/projects/${projectId}/plans/${task.plan.id}`}
                className="task-plan-link"
              >
                <span className="task-plan-icon"></span>
                <span className="task-plan-title">{task.plan.title}</span>
              </Link>
            </div>
          )}
        </div>

        {/* Sidebar - Dependencies */}
        <div className="task-detail-page__sidebar">
          {/* Dependency Graph Visualization */}
          <div className="task-card-section task-dependency-graph">
            <h2 className="section-title">Dependencies</h2>
            <DependencyGraph
              task={task}
              projectId={projectId}
            />
          </div>

          {/* Blocked By */}
          {task.blocked_by.length > 0 && (
            <div className="task-card-section task-blocked-section">
              <h2 className="section-title">
                <span className="section-title-icon"></span>
                Blocked By ({task.blocked_by.length})
              </h2>
              <p className="section-hint">
                Complete these tasks to unblock this task:
              </p>
              <ul className="task-dep-list">
                {task.blocked_by.map((depId) => {
                  const depTask = task.blocked_by_tasks?.find(
                    (t) => t.id === depId
                  )
                  return (
                    <li key={depId} className="task-dep-item">
                      <Link
                        to={`/projects/${projectId}/tasks/${depId}`}
                        className="task-dep-link"
                      >
                        <span className="task-dep-icon"></span>
                        <span className="task-dep-title">
                          {depTask?.title || depId}
                        </span>
                        {depTask && (
                          <TaskStatusBadge status={depTask.status} />
                        )}
                      </Link>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}

          {/* Blocking */}
          {task.blocking_tasks && task.blocking_tasks.length > 0 && (
            <div className="task-card-section task-blocking-section">
              <h2 className="section-title">
                <span className="section-title-icon"></span>
                Blocking ({task.blocking_tasks.length})
              </h2>
              <p className="section-hint">
                These tasks are waiting for this task:
              </p>
              <ul className="task-dep-list">
                {task.blocking_tasks.map((blockingTask) => (
                  <li key={blockingTask.id} className="task-dep-item">
                    <Link
                      to={`/projects/${projectId}/tasks/${blockingTask.id}`}
                      className="task-dep-link"
                    >
                      <span className="task-dep-icon"></span>
                      <span className="task-dep-title">
                        {blockingTask.title}
                      </span>
                      <TaskStatusBadge status={blockingTask.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* No Dependencies */}
          {task.blocked_by.length === 0 &&
            (!task.blocking_tasks || task.blocking_tasks.length === 0) && (
              <div className="task-card-section task-no-deps">
                <h2 className="section-title">Dependencies</h2>
                <p className="task-empty-text">
                  This task has no dependencies and is not blocking any other
                  tasks.
                </p>
              </div>
            )}
        </div>
      </div>
    </div>
  )
}

interface DependencyGraphProps {
  task: TaskWithDetails
  projectId: string
}

function DependencyGraph({ task, projectId }: DependencyGraphProps) {
  const hasBlockedBy = task.blocked_by.length > 0
  const hasBlocking = task.blocking_tasks && task.blocking_tasks.length > 0

  if (!hasBlockedBy && !hasBlocking) {
    return (
      <div className="dep-graph-empty">
        <span className="dep-graph-empty-icon"></span>
        <p>No dependencies</p>
      </div>
    )
  }

  return (
    <div className="dep-graph">
      {/* Blocked By (upstream) */}
      {hasBlockedBy && (
        <div className="dep-graph__section dep-graph__upstream">
          <div className="dep-graph__label">Must complete first</div>
          <div className="dep-graph__nodes">
            {task.blocked_by_tasks?.map((depTask) => (
              <Link
                key={depTask.id}
                to={`/projects/${projectId}/tasks/${depTask.id}`}
                className={`dep-graph__node dep-graph__node--${depTask.status}`}
              >
                <span className="dep-graph__node-title">{depTask.title}</span>
                <TaskStatusBadge status={depTask.status} />
              </Link>
            ))}
          </div>
          <div className="dep-graph__arrow dep-graph__arrow--down"></div>
        </div>
      )}

      {/* Current Task */}
      <div className="dep-graph__current">
        <div
          className="dep-graph__current-node"
          style={{
            borderColor: TASK_STATUS_CONFIG[task.status].color,
          }}
        >
          <span className="dep-graph__current-label">Current Task</span>
          <span className="dep-graph__current-title">{task.title}</span>
          <TaskStatusBadge status={task.status} />
        </div>
      </div>

      {/* Blocking (downstream) */}
      {hasBlocking && (
        <div className="dep-graph__section dep-graph__downstream">
          <div className="dep-graph__arrow dep-graph__arrow--down"></div>
          <div className="dep-graph__label">Waiting for this</div>
          <div className="dep-graph__nodes">
            {task.blocking_tasks?.map((blockingTask) => (
              <Link
                key={blockingTask.id}
                to={`/projects/${projectId}/tasks/${blockingTask.id}`}
                className={`dep-graph__node dep-graph__node--${blockingTask.status}`}
              >
                <span className="dep-graph__node-title">
                  {blockingTask.title}
                </span>
                <TaskStatusBadge status={blockingTask.status} />
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
