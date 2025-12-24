import { useState, useEffect, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch, ApiError } from '../utils/api'
import { LoadingSpinner } from '../components/LoadingSpinner'
import type { Project, ProjectCreate, PaginatedResponse } from '../types/project'

interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: (project: Project) => void
}

function CreateProjectModal({ isOpen, onClose, onCreated }: CreateProjectModalProps) {
  const [name, setName] = useState('')
  const [gitUrl, setGitUrl] = useState('')
  const [mainBranch, setMainBranch] = useState('main')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      const projectData: ProjectCreate = {
        name: name.trim(),
        git_url: gitUrl.trim(),
        main_branch: mainBranch.trim() || 'main',
      }

      const newProject = await apiFetch<Project>('/projects', {
        method: 'POST',
        body: JSON.stringify(projectData),
      })

      onCreated(newProject)
      // Reset form
      setName('')
      setGitUrl('')
      setMainBranch('main')
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to create project')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      setError(null)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create New Project</h3>
          <button
            className="modal-close-btn"
            onClick={handleClose}
            disabled={isSubmitting}
            aria-label="Close"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label htmlFor="project-name">Project Name</label>
            <input
              id="project-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Awesome Project"
              required
              disabled={isSubmitting}
            />
          </div>

          <div className="form-group">
            <label htmlFor="git-url">Git Repository URL</label>
            <input
              id="git-url"
              type="text"
              value={gitUrl}
              onChange={(e) => setGitUrl(e.target.value)}
              placeholder="/path/to/repo or https://github.com/user/repo.git"
              required
              disabled={isSubmitting}
            />
            <span className="form-hint">
              Local path or remote URL (the repository must be accessible)
            </span>
          </div>

          <div className="form-group">
            <label htmlFor="main-branch">Main Branch</label>
            <input
              id="main-branch"
              type="text"
              value={mainBranch}
              onChange={(e) => setMainBranch(e.target.value)}
              placeholder="main"
              disabled={isSubmitting}
            />
            <span className="form-hint">The primary branch for this repository</span>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)

  const fetchProjects = async (pageNum: number = 1) => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiFetch<PaginatedResponse<Project>>(
        `/projects?page=${pageNum}&limit=20`
      )
      setProjects(response.items)
      setPage(response.page)
      setTotalPages(response.pages)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load projects')
      }
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleProjectCreated = (newProject: Project) => {
    setIsModalOpen(false)
    // Add the new project to the top of the list
    setProjects((prev) => [newProject, ...prev])
  }

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchProjects(newPage)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getRepoName = (gitUrl: string) => {
    // Extract repo name from URL or path
    const parts = gitUrl.replace(/\.git$/, '').split('/')
    return parts[parts.length - 1] || gitUrl
  }

  return (
    <div className="page-content">
      <div className="page-header">
        <div>
          <h2>Projects</h2>
          <p className="page-subtitle">Manage your project repositories</p>
        </div>
        <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
          <svg
            className="btn-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Project
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Loading projects..." />
      ) : error ? (
        <div className="error-state">
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={() => fetchProjects()}>
            Try Again
          </button>
        </div>
      ) : projects.length === 0 ? (
        <div className="empty-state">
          <svg
            className="empty-state-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
          </svg>
          <h3>No projects yet</h3>
          <p>Create your first project to get started</p>
          <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
            Create Project
          </button>
        </div>
      ) : (
        <>
          <div className="projects-grid">
            {projects.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="project-card"
              >
                <div className="project-card-header">
                  <svg
                    className="project-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
                  </svg>
                  <h3 className="project-name">{project.name}</h3>
                </div>
                <div className="project-card-body">
                  <div className="project-info">
                    <span className="project-info-label">Repository</span>
                    <span className="project-info-value" title={project.git_url}>
                      {getRepoName(project.git_url)}
                    </span>
                  </div>
                  <div className="project-info">
                    <span className="project-info-label">Branch</span>
                    <span className="project-info-value">{project.main_branch}</span>
                  </div>
                </div>
                <div className="project-card-footer">
                  <span className="project-created">
                    Created {formatDate(project.created_at)}
                  </span>
                </div>
              </Link>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button
                className="pagination-btn"
                onClick={() => handlePageChange(page - 1)}
                disabled={page <= 1}
              >
                Previous
              </button>
              <span className="pagination-info">
                Page {page} of {totalPages}
              </span>
              <button
                className="pagination-btn"
                onClick={() => handlePageChange(page + 1)}
                disabled={page >= totalPages}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      <CreateProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={handleProjectCreated}
      />
    </div>
  )
}
