import { useState } from 'react'
import './EndSessionButton.css'

interface EndSessionButtonProps {
  onEndSession: (force: boolean) => Promise<void>
  isEnding: boolean
  disabled?: boolean
}

export function EndSessionButton({
  onEndSession,
  isEnding,
  disabled = false,
}: EndSessionButtonProps) {
  const [showConfirmModal, setShowConfirmModal] = useState(false)

  const handleClick = () => {
    setShowConfirmModal(true)
  }

  const handleConfirm = async (force: boolean = false) => {
    setShowConfirmModal(false)
    await onEndSession(force)
  }

  const handleCancel = () => {
    setShowConfirmModal(false)
  }

  const isDisabled = disabled || isEnding

  return (
    <>
      <button
        className={`end-session-button ${isEnding ? 'end-session-button--ending' : ''}`}
        onClick={handleClick}
        disabled={isDisabled}
        title="End the coding session for this task"
      >
        {isEnding && <span className="end-session-button__spinner" />}
        <span className="end-session-button__icon">
          {isEnding ? '' : '\u25A0'}
        </span>
        <span>{isEnding ? 'Ending...' : 'End Session'}</span>
      </button>

      {showConfirmModal && (
        <div className="session-modal-overlay" onClick={handleCancel}>
          <div
            className="session-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="session-modal__title">End Coding Session</h3>
            <div className="session-modal__body">
              <p>This will:</p>
              <ul className="session-modal__list">
                <li>Remove the git worktree (clean up local files)</li>
                <li>Keep your feature branch and all commits</li>
                <li>Mark the session as ended</li>
              </ul>
              <div className="session-modal__warning">
                Make sure you have committed and pushed all your changes before ending the session!
              </div>
            </div>
            <div className="session-modal__actions">
              <button className="btn btn-secondary" onClick={handleCancel}>
                Cancel
              </button>
              <button
                className="btn btn-danger"
                onClick={() => handleConfirm(false)}
              >
                End Session
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
