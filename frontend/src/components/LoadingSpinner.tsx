interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large'
  message?: string
  fullScreen?: boolean
}

export function LoadingSpinner({
  size = 'medium',
  message,
  fullScreen = false,
}: LoadingSpinnerProps) {
  const sizeClass = `spinner-${size}`
  const containerClass = fullScreen
    ? 'loading-container loading-fullscreen'
    : 'loading-container loading-inline'

  return (
    <div className={containerClass}>
      <div className={`spinner ${sizeClass}`} />
      {message && <p className="loading-message">{message}</p>}
    </div>
  )
}
