import { NavLink, useParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function Sidebar() {
  const { user } = useAuth()
  const { projectId } = useParams<{ projectId: string }>()

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-logo">ATC</h1>
      </div>

      <nav className="sidebar-nav">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `nav-item ${isActive ? 'nav-item-active' : ''}`
          }
        >
          <svg
            className="nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
            <polyline points="9,22 9,12 15,12 15,22" />
          </svg>
          Dashboard
        </NavLink>

        <NavLink
          to="/projects"
          className={({ isActive }) =>
            `nav-item ${isActive ? 'nav-item-active' : ''}`
          }
        >
          <svg
            className="nav-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
          </svg>
          Projects
        </NavLink>

        {projectId && (
          <>
            <div className="nav-divider" />
            <div className="nav-section-label">Current Project</div>
            <NavLink
              to={`/projects/${projectId}`}
              end
              className={({ isActive }) =>
                `nav-item nav-item-nested ${isActive ? 'nav-item-active' : ''}`
              }
            >
              <svg
                className="nav-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              Overview
            </NavLink>
            <NavLink
              to={`/projects/${projectId}/plans`}
              className={({ isActive }) =>
                `nav-item nav-item-nested ${isActive ? 'nav-item-active' : ''}`
              }
            >
              <svg
                className="nav-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14,2 14,8 20,8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10,9 9,9 8,9" />
              </svg>
              Plans
            </NavLink>
            <NavLink
              to={`/projects/${projectId}/tasks`}
              className={({ isActive }) =>
                `nav-item nav-item-nested ${isActive ? 'nav-item-active' : ''}`
              }
            >
              <svg
                className="nav-icon"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
              </svg>
              Tasks
            </NavLink>
          </>
        )}
      </nav>

      <div className="sidebar-footer">
        {user && (
          <div className="sidebar-user">
            {user.avatar_url && (
              <img
                src={user.avatar_url}
                alt={user.display_name || user.git_handle}
                className="sidebar-avatar"
              />
            )}
            <span className="sidebar-username">
              {user.display_name || user.git_handle}
            </span>
          </div>
        )}
      </div>
    </aside>
  )
}
