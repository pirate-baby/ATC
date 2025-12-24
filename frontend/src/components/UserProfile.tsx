import { useAuth } from '../contexts/AuthContext'

export function UserProfile() {
  const { user, logout } = useAuth()

  if (!user) {
    return null
  }

  return (
    <div className="user-profile">
      {user.avatar_url && (
        <img
          src={user.avatar_url}
          alt={user.display_name || user.git_handle}
          className="user-avatar"
        />
      )}
      <div className="user-info">
        <span className="user-name">{user.display_name || user.git_handle}</span>
        <span className="user-handle">@{user.git_handle}</span>
      </div>
      <button className="logout-btn" onClick={logout}>
        Logout
      </button>
    </div>
  )
}
