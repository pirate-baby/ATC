import { useCallback, useState } from 'react'
import {
  Plan,
  PlanGenerateRequest,
  PlanGenerationStatus,
  ProcessingStatus,
} from '../types/plan'
import { apiFetch, ApiError } from '../utils/api'
import { usePolling } from './usePolling'

export interface UsePlanGenerationOptions {
  // Plan ID to generate content for
  planId: string
  // Callback when generation completes successfully
  onComplete?: (plan: Plan) => void
  // Callback when generation fails
  onError?: (error: Error) => void
  // Polling interval in milliseconds (default: 2500)
  pollInterval?: number
}

export interface UsePlanGenerationResult {
  // Whether generation is in progress
  isGenerating: boolean
  // Current generation status
  status: ProcessingStatus | null
  // Error message if generation failed
  error: string | null
  // Generated content (available when completed)
  content: string | null
  // Start the generation process
  startGeneration: (context?: string) => Promise<void>
  // Reset the hook state
  reset: () => void
}

export function usePlanGeneration({
  planId,
  onComplete,
  onError,
  pollInterval = 2500,
}: UsePlanGenerationOptions): UsePlanGenerationResult {
  const [isGenerating, setIsGenerating] = useState(false)
  const [status, setStatus] = useState<ProcessingStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [content, setContent] = useState<string | null>(null)
  const [pollingEnabled, setPollingEnabled] = useState(false)

  // Fetch generation status
  const fetchStatus = useCallback(async () => {
    const result = await apiFetch<PlanGenerationStatus>(
      `/plans/${planId}/generation-status`
    )
    return result
  }, [planId])

  // Determine if polling should stop
  const shouldStopPolling = useCallback((data: PlanGenerationStatus) => {
    return (
      data.processing_status === ProcessingStatus.COMPLETED ||
      data.processing_status === ProcessingStatus.FAILED
    )
  }, [])

  // Handle polling completion
  const handlePollingComplete = useCallback(
    async (data: PlanGenerationStatus) => {
      setPollingEnabled(false)
      setStatus(data.processing_status)

      if (data.processing_status === ProcessingStatus.COMPLETED) {
        setContent(data.content)
        setIsGenerating(false)

        // Fetch the updated plan to pass to onComplete
        try {
          const updatedPlan = await apiFetch<Plan>(`/plans/${planId}`)
          onComplete?.(updatedPlan)
        } catch (err) {
          // Even if fetching the plan fails, generation succeeded
          console.error('Failed to fetch updated plan:', err)
          onComplete?.({
            id: planId,
            content: data.content,
          } as Plan)
        }
      } else if (data.processing_status === ProcessingStatus.FAILED) {
        const errorMsg = data.processing_error || 'Generation failed'
        setError(errorMsg)
        setIsGenerating(false)
        onError?.(new Error(errorMsg))
      }
    },
    [planId, onComplete, onError]
  )

  // Handle polling errors
  const handlePollingError = useCallback(
    (err: Error) => {
      const errorMsg = err instanceof ApiError ? err.message : 'Failed to check generation status'
      setError(errorMsg)
      setIsGenerating(false)
      setPollingEnabled(false)
      onError?.(err)
    },
    [onError]
  )

  // Set up polling
  const { data: pollingData } = usePolling<PlanGenerationStatus>({
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

  // Start the generation process
  const startGeneration = useCallback(
    async (context?: string) => {
      setIsGenerating(true)
      setError(null)
      setContent(null)
      setStatus(ProcessingStatus.PENDING)

      try {
        const request: PlanGenerateRequest = {}
        if (context) {
          request.context = context
        }

        // POST to initiate generation (returns 202 Accepted)
        await apiFetch<void>(`/plans/${planId}/generate`, {
          method: 'POST',
          body: JSON.stringify(request),
        })

        // Start polling for status
        setPollingEnabled(true)
      } catch (err) {
        const errorMsg =
          err instanceof ApiError ? err.message : 'Failed to start generation'
        setError(errorMsg)
        setIsGenerating(false)
        setStatus(ProcessingStatus.FAILED)
        onError?.(err instanceof Error ? err : new Error(errorMsg))
      }
    },
    [planId, onError]
  )

  // Reset the hook state
  const reset = useCallback(() => {
    setIsGenerating(false)
    setStatus(null)
    setError(null)
    setContent(null)
    setPollingEnabled(false)
  }, [])

  return {
    isGenerating,
    status,
    error,
    content,
    startGeneration,
    reset,
  }
}
