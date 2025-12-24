import { ProcessingStatus } from '../types/plan'
import './GenerationProgressIndicator.css'

interface GenerationProgressIndicatorProps {
  status: ProcessingStatus | null
  error?: string | null
  onRetry?: () => void
}

export function GenerationProgressIndicator({
  status,
  error,
  onRetry,
}: GenerationProgressIndicatorProps) {
  if (!status || status === ProcessingStatus.COMPLETED) {
    return null
  }

  const isGenerating =
    status === ProcessingStatus.PENDING ||
    status === ProcessingStatus.GENERATING
  const isFailed = status === ProcessingStatus.FAILED

  return (
    <div
      className={`generation-progress ${isFailed ? 'generation-progress--failed' : ''}`}
    >
      <div className="generation-progress__content">
        {isGenerating && (
          <>
            <div className="generation-progress__spinner">
              <div className="generation-progress__spinner-ring" />
              <div className="generation-progress__spinner-icon">✨</div>
            </div>
            <div className="generation-progress__text">
              <h4 className="generation-progress__title">
                {status === ProcessingStatus.PENDING
                  ? 'Starting generation...'
                  : 'Claude is generating your plan content'}
              </h4>
              <p className="generation-progress__description">
                {status === ProcessingStatus.PENDING
                  ? 'Queuing your request...'
                  : 'This may take a minute. Claude is analyzing your project and crafting a detailed plan.'}
              </p>
            </div>
          </>
        )}

        {isFailed && (
          <>
            <div className="generation-progress__error-icon">!</div>
            <div className="generation-progress__text">
              <h4 className="generation-progress__title">Generation Failed</h4>
              <p className="generation-progress__description">
                {error || 'An unexpected error occurred during generation.'}
              </p>
              {onRetry && (
                <button
                  className="generation-progress__retry-button"
                  onClick={onRetry}
                >
                  Try Again
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {isGenerating && (
        <div className="generation-progress__steps">
          <div
            className={`generation-progress__step ${status === ProcessingStatus.PENDING ? 'generation-progress__step--active' : 'generation-progress__step--completed'}`}
          >
            <span className="generation-progress__step-dot" />
            <span>Queued</span>
          </div>
          <div
            className={`generation-progress__step ${status === ProcessingStatus.GENERATING ? 'generation-progress__step--active' : ''}`}
          >
            <span className="generation-progress__step-dot" />
            <span>Generating</span>
          </div>
          <div className="generation-progress__step">
            <span className="generation-progress__step-dot" />
            <span>Complete</span>
          </div>
        </div>
      )}
    </div>
  )
}
