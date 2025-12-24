import { useState } from 'react'
import { ProcessingStatus } from '../types/plan'
import './GenerateContentButton.css'

interface GenerateContentButtonProps {
  onGenerate: (context?: string) => Promise<void>
  isGenerating: boolean
  status: ProcessingStatus | null
  disabled?: boolean
  hasContent?: boolean
}

export function GenerateContentButton({
  onGenerate,
  isGenerating,
  status,
  disabled = false,
  hasContent = false,
}: GenerateContentButtonProps) {
  const [showContextModal, setShowContextModal] = useState(false)
  const [context, setContext] = useState('')

  const handleClick = () => {
    if (hasContent) {
      // If content exists, show confirmation
      setShowContextModal(true)
    } else {
      // Start generation directly
      handleGenerate()
    }
  }

  const handleGenerate = async () => {
    setShowContextModal(false)
    await onGenerate(context || undefined)
    setContext('')
  }

  const handleCancel = () => {
    setShowContextModal(false)
    setContext('')
  }

  const isDisabled = disabled || isGenerating

  const buttonText = isGenerating
    ? 'Generating...'
    : hasContent
      ? 'Regenerate Content'
      : 'Generate Content'

  return (
    <>
      <button
        className={`generate-button ${isGenerating ? 'generate-button--generating' : ''}`}
        onClick={handleClick}
        disabled={isDisabled}
        title={
          status === ProcessingStatus.FAILED
            ? 'Previous generation failed. Click to retry.'
            : undefined
        }
      >
        {isGenerating && <span className="generate-button__spinner" />}
        <span className="generate-button__icon">
          {isGenerating ? '' : '✨'}
        </span>
        <span>{buttonText}</span>
      </button>

      {showContextModal && (
        <div className="generate-modal-overlay" onClick={handleCancel}>
          <div
            className="generate-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="generate-modal__title">
              {hasContent ? 'Regenerate Plan Content' : 'Generate Plan Content'}
            </h3>
            {hasContent && (
              <p className="generate-modal__warning">
                This will replace the existing content. Are you sure?
              </p>
            )}
            <div className="generate-modal__field">
              <label htmlFor="context-input">
                Additional Context (optional)
              </label>
              <textarea
                id="context-input"
                className="generate-modal__textarea"
                value={context}
                onChange={(e) => setContext(e.target.value)}
                placeholder="Provide any additional context or requirements for Claude..."
                rows={4}
              />
              <p className="generate-modal__hint">
                This context will be included in the prompt to Claude when generating the plan content.
              </p>
            </div>
            <div className="generate-modal__actions">
              <button
                className="btn-secondary"
                onClick={handleCancel}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={handleGenerate}
              >
                {hasContent ? 'Regenerate' : 'Generate'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
