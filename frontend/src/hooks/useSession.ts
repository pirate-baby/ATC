import { useState, useCallback } from 'react'
import { apiFetch, ApiError } from '../utils/api'
import { StartSessionResponse } from '../types/session'
import { Task } from '../types/task'

interface UseSessionOptions {
  onSessionStarted?: (response: StartSessionResponse) => void
  onSessionEnded?: (task: Task) => void
  onError?: (error: string) => void
}

interface UseSessionReturn {
  isStarting: boolean
  isEnding: boolean
  error: string | null
  startSession: (taskId: string) => Promise<StartSessionResponse | null>
  endSession: (taskId: string, force?: boolean) => Promise<Task | null>
  clearError: () => void
}

export function useSession(options: UseSessionOptions = {}): UseSessionReturn {
  const { onSessionStarted, onSessionEnded, onError } = options

  const [isStarting, setIsStarting] = useState(false)
  const [isEnding, setIsEnding] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  const startSession = useCallback(
    async (taskId: string): Promise<StartSessionResponse | null> => {
      setIsStarting(true)
      setError(null)

      try {
        const response = await apiFetch<StartSessionResponse>(
          `/tasks/${taskId}/start-session`,
          { method: 'POST' }
        )
        onSessionStarted?.(response)
        return response
      } catch (err) {
        const message =
          err instanceof ApiError
            ? err.message
            : 'Failed to start coding session'
        setError(message)
        onError?.(message)
        return null
      } finally {
        setIsStarting(false)
      }
    },
    [onSessionStarted, onError]
  )

  const endSession = useCallback(
    async (taskId: string, force: boolean = false): Promise<Task | null> => {
      setIsEnding(true)
      setError(null)

      try {
        const url = `/tasks/${taskId}/end-session${force ? '?force=true' : ''}`
        const response = await apiFetch<Task>(url, { method: 'POST' })
        onSessionEnded?.(response)
        return response
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : 'Failed to end coding session'
        setError(message)
        onError?.(message)
        return null
      } finally {
        setIsEnding(false)
      }
    },
    [onSessionEnded, onError]
  )

  return {
    isStarting,
    isEnding,
    error,
    startSession,
    endSession,
    clearError,
  }
}
