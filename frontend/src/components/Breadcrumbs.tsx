import { Link, useLocation, useParams } from 'react-router-dom'

interface BreadcrumbItem {
  label: string
  path: string
}

export function Breadcrumbs() {
  const location = useLocation()
  const { projectId } = useParams<{ projectId: string }>()

  const breadcrumbs: BreadcrumbItem[] = []

  // Build breadcrumbs based on current path
  const pathParts = location.pathname.split('/').filter(Boolean)

  if (pathParts.length === 0) {
    breadcrumbs.push({ label: 'Dashboard', path: '/' })
  } else if (pathParts[0] === 'projects') {
    breadcrumbs.push({ label: 'Projects', path: '/projects' })

    if (projectId) {
      breadcrumbs.push({
        label: `Project ${projectId.slice(0, 8)}...`,
        path: `/projects/${projectId}`,
      })

      if (pathParts[2] === 'plans') {
        breadcrumbs.push({
          label: 'Plans',
          path: `/projects/${projectId}/plans`,
        })
      } else if (pathParts[2] === 'tasks') {
        breadcrumbs.push({
          label: 'Tasks',
          path: `/projects/${projectId}/tasks`,
        })
      }
    }
  }

  if (breadcrumbs.length === 0) {
    return null
  }

  return (
    <nav className="breadcrumbs" aria-label="Breadcrumb">
      <ol className="breadcrumb-list">
        {breadcrumbs.map((crumb, index) => (
          <li key={crumb.path} className="breadcrumb-item">
            {index > 0 && <span className="breadcrumb-separator">/</span>}
            {index === breadcrumbs.length - 1 ? (
              <span className="breadcrumb-current">{crumb.label}</span>
            ) : (
              <Link to={crumb.path} className="breadcrumb-link">
                {crumb.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}
