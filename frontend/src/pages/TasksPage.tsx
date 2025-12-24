import { useState, useEffect, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { apiFetch, ApiError } from '../utils/api'
import { LoadingSpinner } from '../components/LoadingSpinner'
import type { PaginatedResponse } from '../types/project'
import {
  Task,
  TaskWithDetails,
  TaskStatus,
  TASK_STATUS_OPTIONS,
  TASK_STATUS_CONFIG,
} from '../types/task'
import './TasksPage.css'

function TaskStatusBadge({ status }: { status: TaskStatus }) {
  const config = TASK_STATUS_CONFIG[status]
  return (
    <span
      className="task-status-badge"
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

function TaskDependencyBadge({
  count,
  type,
}: {
  count: number
  type: 'blocking' | 'blocked_by'
}) {
  if (count === 0) return null

  const isBlocking = type === 'blocking'

  return (
    <span
      className={`task-dependency-badge ${isBlocking ? 'task-dependency-badge--blocking' : 'task-dependency-badge--blocked'}`}
      title={
        isBlocking
          ? `Blocking ${count} other task${count !== 1 ? 's' : ''}`
          : `Blocked by ${count} task${count !== 1 ? 's' : ''}`
      }
    >
      {isBlocking ? '' : ''} {count}
    </span>
  )
}

export function TasksPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const [tasks, setTasks] = useState<Task[]>([])
  const [selectedTask, setSelectedTask] = useState<TaskWithDetails | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingDetail, setIsLoadingDetail] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [statusFilter, setStatusFilter] = useState<TaskStatus | ''>('')

  const fetchTasks = useCallback(
    async (pageNum: number = 1, status: TaskStatus | '' = '') => {
      if (!projectId) return

      setIsLoading(true)
      setError(null)

      try {
        let url = `/projects/${projectId}/tasks?page=${pageNum}&limit=20`
        if (status) {
          url += `&status=${status}`
        }

        const response = await apiFetch<PaginatedResponse<Task>>(url)
        setTasks(response.items)
        setPage(response.page)
        setTotalPages(response.pages)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load tasks')
        }
      } finally {
        setIsLoading(false)
      }
    },
    [projectId]
  )

  useEffect(() => {
    if (projectId) {
      fetchTasks(1, statusFilter)
    }
  }, [projectId, statusFilter, fetchTasks])

  const fetchTaskDetails = useCallback(async (taskId: string) => {
    setIsLoadingDetail(true)

    try {
      const data = await apiFetch<TaskWithDetails>(`/tasks/${taskId}`)
      setSelectedTask(data)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load task details')
      }
    } finally {
      setIsLoadingDetail(false)
    }
  }, [])

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchTasks(newPage, statusFilter)
    }
  }

  const handleStatusFilterChange = (newStatus: TaskStatus | '') => {
    setStatusFilter(newStatus)
    setPage(1)
  }

  const handleTaskClick = (task: Task) => {
    fetchTaskDetails(task.id)
  }

  const handleCloseTaskDetail = () => {
    setSelectedTask(null)
  }

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

  // Build a map of task IDs to titles for dependency display
  const taskTitleMap = new Map(tasks.map((t) => [t.id, t.title]))

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
    <div className="page-content tasks-page">
      <div className="page-header tasks-page__header">
        <div>
          <h2>Tasks</h2>
          <p className="page-subtitle">
            Manage implementation tasks for this project
          </p>
        </div>
      </div>

      {/* Status Filter */}
      <div className="filter-bar">
        <div className="form-group filter-group">
          <label htmlFor="status-filter">Filter by Status</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) =>
              handleStatusFilterChange(e.target.value as TaskStatus | '')
            }
          >
            {TASK_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        <div className="filter-summary">
          {tasks.length > 0 && (
            <span className="filter-count">
              {tasks.length} task{tasks.length !== 1 ? 's' : ''}
              {statusFilter && ` in ${TASK_STATUS_CONFIG[statusFilter].label}`}
            </span>
          )}
        </div>
      </div>

      {error && (
        <div className="error-message tasks-page__error">
          {error}
          <button
            className="error-dismiss"
            onClick={() => setError(null)}
            aria-label="Dismiss"
          >
            x
          </button>
        </div>
      )}

      <div className="tasks-page__content">
        {/* Task List */}
        <div className="tasks-page__list-section">
          {isLoading ? (
            <LoadingSpinner message="Loading tasks..." />
          ) : tasks.length === 0 ? (
            <div className="empty-state tasks-page__empty">
              <svg
                className="empty-state-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
              <h3>
                {statusFilter ? 'No tasks match this filter' : 'No tasks yet'}
              </h3>
              <p>
                {statusFilter
                  ? 'Try a different status filter'
                  : 'Tasks will appear here when spawned from approved plans'}
              </p>
              <Link
                to={`/projects/${projectId}/plans`}
                className="btn btn-primary"
              >
                View Plans
              </Link>
            </div>
          ) : (
            <>
              <div className="tasks-list">
                {tasks.map((task) => (
                  <div
                    key={task.id}
                    className={`task-card ${selectedTask?.id === task.id ? 'task-card--selected' : ''} ${task.blocked_by.length > 0 ? 'task-card--blocked' : ''}`}
                    onClick={() => handleTaskClick(task)}
                  >
                    <div className="task-card__header">
                      <div className="task-card__title-row">
                        <svg
                          className="task-icon"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                          <path d="M9 12l2 2 4-4" />
                        </svg>
                        <h3 className="task-title">{task.title}</h3>
                      </div>
                      <div className="task-badges">
                        <TaskStatusBadge status={task.status} />
                        <TaskDependencyBadge
                          count={task.blocked_by.length}
                          type="blocked_by"
                        />
                      </div>
                    </div>
                    {task.description && (
                      <div className="task-card__body">
                        <p className="task-excerpt">
                          {task.description.length > 120
                            ? task.description.substring(0, 120) + '...'
                            : task.description}
                        </p>
                      </div>
                    )}
                    {task.blocked_by.length > 0 && (
                      <div className="task-card__dependencies">
                        <span className="task-card__dep-label">
                          Blocked by:
                        </span>
                        {task.blocked_by.slice(0, 3).map((depId) => (
                          <span key={depId} className="task-card__dep-item">
                            {taskTitleMap.get(depId) || depId.slice(0, 8)}
                          </span>
                        ))}
                        {task.blocked_by.length > 3 && (
                          <span className="task-card__dep-more">
                            +{task.blocked_by.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                    <div className="task-card__footer">
                      <span className="task-meta">
                        Created {formatRelativeTime(task.created_at)}
                        {task.updated_at &&
                          ` - Updated ${formatRelativeTime(task.updated_at)}`}
                      </span>
                      {task.branch_name && (
                        <span className="task-branch" title={task.branch_name}>
                          {task.branch_name}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {totalPages > 1 && (
                <div className="pagination tasks-page__pagination">
                  <button
                    className="pagination-btn btn btn-secondary btn-small"
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page <= 1}
                  >
                    Previous
                  </button>
                  <span className="pagination-info tasks-page__page-info">
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

        {/* Task Detail View */}
        <div className="tasks-page__detail-section">
          {isLoadingDetail && <LoadingSpinner message="Loading task..." />}

          {!isLoadingDetail && selectedTask && (
            <TaskDetailPanel
              task={selectedTask}
              projectId={projectId}
              taskTitleMap={taskTitleMap}
              onClose={handleCloseTaskDetail}
            />
          )}

          {!isLoadingDetail && !selectedTask && tasks.length > 0 && (
            <div className="tasks-page__no-selection">
              <div className="tasks-page__no-selection-icon">{''}</div>
              <p>Select a task from the list to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

interface TaskDetailPanelProps {
  task: TaskWithDetails
  projectId: string
  taskTitleMap: Map<string, string>
  onClose: () => void
}

function TaskDetailPanel({
  task,
  projectId,
  taskTitleMap,
  onClose,
}: TaskDetailPanelProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const config = TASK_STATUS_CONFIG[task.status]

  return (
    <div className="task-detail">
      <div className="task-detail__header">
        <div className="task-detail__title-section">
          <h2 className="task-detail__title">{task.title}</h2>
          <div className="task-detail__badges">
            <span
              className="task-detail__status"
              style={{
                color: config.color,
                backgroundColor: config.bgColor,
              }}
            >
              {config.label}
            </span>
          </div>
        </div>
        <div className="task-detail__actions">
          <Link
            to={`/projects/${projectId}/tasks/${task.id}`}
            className="btn btn-primary"
          >
            Full View
          </Link>
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>

      <div className="task-detail__meta">
        <div className="task-detail__meta-item">
          <span className="task-detail__meta-label">Created</span>
          <span className="task-detail__meta-value">
            {formatDate(task.created_at)}
          </span>
        </div>
        {task.updated_at && (
          <div className="task-detail__meta-item">
            <span className="task-detail__meta-label">Updated</span>
            <span className="task-detail__meta-value">
              {formatDate(task.updated_at)}
            </span>
          </div>
        )}
        {task.branch_name && (
          <div className="task-detail__meta-item">
            <span className="task-detail__meta-label">Branch</span>
            <span className="task-detail__meta-value task-detail__branch">
              {task.branch_name}
            </span>
          </div>
        )}
      </div>

      {/* Description */}
      <div className="task-detail__section">
        <h3 className="task-detail__section-title">Description</h3>
        {task.description ? (
          <div className="task-detail__description">{task.description}</div>
        ) : (
          <p className="task-detail__empty">No description provided</p>
        )}
      </div>

      {/* Dependencies - Blocked By */}
      {task.blocked_by.length > 0 && (
        <div className="task-detail__section task-detail__dependencies">
          <h3 className="task-detail__section-title">
            Blocked By ({task.blocked_by.length})
          </h3>
          <p className="task-detail__dep-hint">
            This task cannot start until the following tasks are completed:
          </p>
          <ul className="task-detail__dep-list">
            {task.blocked_by.map((depId) => {
              const depTask = task.blocked_by_tasks?.find(
                (t) => t.id === depId
              )
              return (
                <li key={depId} className="task-detail__dep-item">
                  <Link
                    to={`/projects/${projectId}/tasks/${depId}`}
                    className="task-detail__dep-link"
                  >
                    <span className="task-detail__dep-icon"></span>
                    <span className="task-detail__dep-title">
                      {depTask?.title || taskTitleMap.get(depId) || depId}
                    </span>
                    {depTask && (
                      <TaskStatusBadge status={depTask.status as TaskStatus} />
                    )}
                  </Link>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {/* Dependencies - Blocking */}
      {task.blocking_tasks && task.blocking_tasks.length > 0 && (
        <div className="task-detail__section task-detail__blocking">
          <h3 className="task-detail__section-title">
            Blocking ({task.blocking_tasks.length})
          </h3>
          <p className="task-detail__dep-hint">
            The following tasks are waiting for this task to complete:
          </p>
          <ul className="task-detail__dep-list">
            {task.blocking_tasks.map((blockingTask) => (
              <li key={blockingTask.id} className="task-detail__dep-item">
                <Link
                  to={`/projects/${projectId}/tasks/${blockingTask.id}`}
                  className="task-detail__dep-link"
                >
                  <span className="task-detail__dep-icon"></span>
                  <span className="task-detail__dep-title">
                    {blockingTask.title}
                  </span>
                  <TaskStatusBadge
                    status={blockingTask.status as TaskStatus}
                  />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Parent Plan */}
      {task.plan && (
        <div className="task-detail__section">
          <h3 className="task-detail__section-title">Parent Plan</h3>
          <Link
            to={`/projects/${projectId}/plans/${task.plan.id}`}
            className="task-detail__plan-link"
          >
            {task.plan.title}
          </Link>
        </div>
      )}
    </div>
  )
}
