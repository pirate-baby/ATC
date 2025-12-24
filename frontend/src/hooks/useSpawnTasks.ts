import { useCallback, useState } from 'react'
import {
  SpawnTasksStatus,
  SpawnedTaskSummary,
  ProcessingStatus,
} from '../types/plan'
import { apiFetch, ApiError } from '../utils/api'
import { usePolling } from './usePolling'

export interface UseSpawnTasksOptions {
  // Plan ID to spawn tasks from
  planId: string
  // Callback when spawning completes successfully
  onComplete?: (tasks: SpawnedTaskSummary[]) => void
  // Callback when spawning fails
  onError?: (error: Error) => void
  // Polling interval in milliseconds (default: 2500)
  pollInterval?: number
}

export interface UseSpawnTasksResult {
  // Whether spawning is in progress
  isSpawning: boolean
  // Current spawn status
  status: ProcessingStatus | null
  // Error message if spawning failed
  error: string | null
  // Number of tasks created (available when completed)
  tasksCreated: number | null
  // Spawned tasks (available when completed)
  spawnedTasks: SpawnedTaskSummary[]
  // Start the spawn process
  startSpawn: () => Promise<void>
  // Reset the hook state
  reset: () => void
}

export function useSpawnTasks({
  planId,
  onComplete,
  onError,
  pollInterval = 2500,
}: UseSpawnTasksOptions): UseSpawnTasksResult {
  const [isSpawning, setIsSpawning] = useState(false)
  const [status, setStatus] = useState<ProcessingStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tasksCreated, setTasksCreated] = useState<number | null>(null)
  const [spawnedTasks, setSpawnedTasks] = useState<SpawnedTaskSummary[]>([])
  const [pollingEnabled, setPollingEnabled] = useState(false)

  // Fetch spawn status
  const fetchStatus = useCallback(async () => {
    const result = await apiFetch<SpawnTasksStatus>(
      `/plans/${planId}/spawn-status`
    )
    return result
  }, [planId])

  // Determine if polling should stop
  const shouldStopPolling = useCallback((data: SpawnTasksStatus) => {
    return (
      data.processing_status === ProcessingStatus.COMPLETED ||
      data.processing_status === ProcessingStatus.FAILED
    )
  }, [])

  // Handle polling completion
  const handlePollingComplete = useCallback(
    async (data: SpawnTasksStatus) => {
      setPollingEnabled(false)
      setStatus(data.processing_status)

      if (data.processing_status === ProcessingStatus.COMPLETED) {
        setTasksCreated(data.tasks_created)
        setIsSpawning(false)

        // Fetch the spawned tasks
        try {
          const tasks = await apiFetch<SpawnedTaskSummary[]>(
            `/plans/${planId}/spawned-tasks`
          )
          setSpawnedTasks(tasks)
          onComplete?.(tasks)
        } catch (err) {
          // Even if fetching tasks fails, spawning succeeded
          console.error('Failed to fetch spawned tasks:', err)
          onComplete?.([])
        }
      } else if (data.processing_status === ProcessingStatus.FAILED) {
        const errorMsg = data.processing_error || 'Task spawning failed'
        setError(errorMsg)
        setIsSpawning(false)
        onError?.(new Error(errorMsg))
      }
    },
    [planId, onComplete, onError]
  )

  // Handle polling errors
  const handlePollingError = useCallback(
    (err: Error) => {
      const errorMsg =
        err instanceof ApiError ? err.message : 'Failed to check spawn status'
      setError(errorMsg)
      setIsSpawning(false)
      setPollingEnabled(false)
      onError?.(err)
    },
    [onError]
  )

  // Set up polling
  const { data: pollingData } = usePolling<SpawnTasksStatus>({
    fetcher: fetchStatus,
    interval: pollInterval,
    shouldStop: shouldStopPolling,
    enabled: pollingEnabled,
    onComplete: handlePollingComplete,
    onError: handlePollingError,
    maxRetries: 5,
  })

  // Update status from polling data
  if (pollingData && pollingData.processing_status !== status) {
    setStatus(pollingData.processing_status)
  }

  // Start the spawn process
  const startSpawn = useCallback(async () => {
    setIsSpawning(true)
    setError(null)
    setTasksCreated(null)
    setSpawnedTasks([])
    setStatus(ProcessingStatus.PENDING)

    try {
      // POST to initiate spawning (returns 202 Accepted)
      await apiFetch<void>(`/plans/${planId}/spawn-tasks`, {
        method: 'POST',
        body: JSON.stringify({}),
      })

      // Start polling for status
      setPollingEnabled(true)
    } catch (err) {
      const errorMsg =
        err instanceof ApiError ? err.message : 'Failed to start task spawning'
      setError(errorMsg)
      setIsSpawning(false)
      setStatus(ProcessingStatus.FAILED)
      onError?.(err instanceof Error ? err : new Error(errorMsg))
    }
  }, [planId, onError])

  // Reset the hook state
  const reset = useCallback(() => {
    setIsSpawning(false)
    setStatus(null)
    setError(null)
    setTasksCreated(null)
    setSpawnedTasks([])
    setPollingEnabled(false)
  }, [])

  return {
    isSpawning,
    status,
    error,
    tasksCreated,
    spawnedTasks,
    startSpawn,
    reset,
  }
}
