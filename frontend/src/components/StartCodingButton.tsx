import { useState } from 'react'
import './StartCodingButton.css'

interface StartCodingButtonProps {
  onStartCoding: () => Promise<void>
  isStarting: boolean
  disabled?: boolean
}

export function StartCodingButton({
  onStartCoding,
  isStarting,
  disabled = false,
}: StartCodingButtonProps) {
  const [showConfirmModal, setShowConfirmModal] = useState(false)

  const handleClick = () => {
    setShowConfirmModal(true)
  }

  const handleConfirm = async () => {
    setShowConfirmModal(false)
    await onStartCoding()
  }

  const handleCancel = () => {
    setShowConfirmModal(false)
  }

  const isDisabled = disabled || isStarting

  return (
    <>
      <button
        className={`start-coding-button ${isStarting ? 'start-coding-button--starting' : ''}`}
        onClick={handleClick}
        disabled={isDisabled}
        title="Start a coding session for this task"
      >
        {isStarting && <span className="start-coding-button__spinner" />}
        <span className="start-coding-button__icon">
          {isStarting ? '' : '\u25B6'}
        </span>
        <span>{isStarting ? 'Starting...' : 'Start Coding'}</span>
      </button>

      {showConfirmModal && (
        <div className="session-modal-overlay" onClick={handleCancel}>
          <div
            className="session-modal"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="session-modal__title">Start Coding Session</h3>
            <div className="session-modal__body">
              <p>This will:</p>
              <ul className="session-modal__list">
                <li>Create a new git worktree for this task</li>
                <li>Create a feature branch for your changes</li>
                <li>Change the task status to "Coding"</li>
              </ul>
              <p className="session-modal__note">
                You can then open the worktree path in your editor to start development.
              </p>
            </div>
            <div className="session-modal__actions">
              <button className="btn btn-secondary" onClick={handleCancel}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={handleConfirm}>
                Start Coding
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
