import { useCallback, useEffect, useRef, useState } from 'react'

export interface UsePollingOptions<T> {
  // Function to fetch data
  fetcher: () => Promise<T>
  // Interval in milliseconds (default: 2000)
  interval?: number
  // Function to determine if polling should stop
  shouldStop?: (data: T) => boolean
  // Whether polling is enabled
  enabled?: boolean
  // Callback when polling completes (shouldStop returns true)
  onComplete?: (data: T) => void
  // Callback on error
  onError?: (error: Error) => void
  // Maximum number of retries on error before stopping
  maxRetries?: number
}

export interface UsePollingResult<T> {
  // Current data from the last successful fetch
  data: T | null
  // Loading state for initial fetch
  isLoading: boolean
  // Error from the last fetch attempt
  error: Error | null
  // Whether polling is currently active
  isPolling: boolean
  // Manually start polling
  startPolling: () => void
  // Manually stop polling
  stopPolling: () => void
  // Reset and restart polling
  reset: () => void
}

export function usePolling<T>({
  fetcher,
  interval = 2000,
  shouldStop,
  enabled = true,
  onComplete,
  onError,
  maxRetries = 3,
}: UsePollingOptions<T>): UsePollingResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const retriesRef = useRef(0)
  const isMountedRef = useRef(true)
  const isPollingRef = useRef(false)

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    isPollingRef.current = false
    if (isMountedRef.current) {
      setIsPolling(false)
    }
  }, [])

  const poll = useCallback(async () => {
    if (!isMountedRef.current || !isPollingRef.current) return

    try {
      const result = await fetcher()

      if (!isMountedRef.current) return

      setData(result)
      setError(null)
      setIsLoading(false)
      retriesRef.current = 0

      // Check if we should stop polling
      if (shouldStop?.(result)) {
        stopPolling()
        onComplete?.(result)
      }
    } catch (err) {
      if (!isMountedRef.current) return

      const error = err instanceof Error ? err : new Error(String(err))
      setError(error)
      setIsLoading(false)
      retriesRef.current++

      onError?.(error)

      // Stop polling if max retries exceeded
      if (retriesRef.current >= maxRetries) {
        stopPolling()
      }
    }
  }, [fetcher, shouldStop, onComplete, onError, maxRetries, stopPolling])

  const startPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }

    isPollingRef.current = true
    setIsPolling(true)
    setIsLoading(true)
    setError(null)
    retriesRef.current = 0

    // Immediately fetch once
    poll()

    // Then set up interval
    intervalRef.current = setInterval(poll, interval)
  }, [poll, interval])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setIsLoading(true)
    retriesRef.current = 0
    startPolling()
  }, [startPolling])

  // Start polling when enabled changes
  useEffect(() => {
    if (enabled) {
      startPolling()
    } else {
      stopPolling()
    }

    return () => {
      stopPolling()
    }
  }, [enabled, startPolling, stopPolling])

  // Track mounted state
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  return {
    data,
    isLoading,
    error,
    isPolling,
    startPolling,
    stopPolling,
    reset,
  }
}
