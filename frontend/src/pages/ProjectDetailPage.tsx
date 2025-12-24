import { useState, useEffect, FormEvent } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { apiFetch, ApiError } from '../utils/api'
import { LoadingSpinner } from '../components/LoadingSpinner'
import type {
  Project,
  ProjectUpdate,
  ProjectSettings,
  ProjectSettingsUpdate,
} from '../types/project'

interface DeleteConfirmModalProps {
  isOpen: boolean
  projectName: string
  onClose: () => void
  onConfirm: () => void
  isDeleting: boolean
}

function DeleteConfirmModal({
  isOpen,
  projectName,
  onClose,
  onConfirm,
  isDeleting,
}: DeleteConfirmModalProps) {
  const [confirmText, setConfirmText] = useState('')

  if (!isOpen) return null

  const canDelete = confirmText === projectName

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-danger" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Delete Project</h3>
          <button
            className="modal-close-btn"
            onClick={onClose}
            disabled={isDeleting}
            aria-label="Close"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="modal-body">
          <div className="delete-warning">
            <svg
              className="warning-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <p>
              This action cannot be undone. This will permanently delete the project
              <strong> {projectName}</strong> and all associated plans and tasks.
            </p>
          </div>

          <div className="form-group">
            <label htmlFor="confirm-delete">
              Type <strong>{projectName}</strong> to confirm
            </label>
            <input
              id="confirm-delete"
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder={projectName}
              disabled={isDeleting}
              autoComplete="off"
            />
          </div>
        </div>

        <div className="modal-actions">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            disabled={isDeleting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn-danger"
            onClick={onConfirm}
            disabled={!canDelete || isDeleting}
          >
            {isDeleting ? 'Deleting...' : 'Delete Project'}
          </button>
        </div>
      </div>
    </div>
  )
}

interface SettingsFormProps {
  settings: ProjectSettings
  onSave: (settings: ProjectSettingsUpdate) => Promise<void>
}

function SettingsForm({ settings, onSave }: SettingsFormProps) {
  const [requiredApprovalsPlan, setRequiredApprovalsPlan] = useState(
    settings.required_approvals_plan
  )
  const [requiredApprovalsTask, setRequiredApprovalsTask] = useState(
    settings.required_approvals_task
  )
  const [autoApprove, setAutoApprove] = useState(settings.auto_approve_main_updates)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    const changed =
      requiredApprovalsPlan !== settings.required_approvals_plan ||
      requiredApprovalsTask !== settings.required_approvals_task ||
      autoApprove !== settings.auto_approve_main_updates
    setHasChanges(changed)
  }, [requiredApprovalsPlan, requiredApprovalsTask, autoApprove, settings])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setIsSaving(true)

    try {
      await onSave({
        required_approvals_plan: requiredApprovalsPlan,
        required_approvals_task: requiredApprovalsTask,
        auto_approve_main_updates: autoApprove,
      })
      setHasChanges(false)
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <form className="settings-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="approvals-plan">Required Approvals for Plans</label>
        <input
          id="approvals-plan"
          type="number"
          min="1"
          max="10"
          value={requiredApprovalsPlan}
          onChange={(e) => setRequiredApprovalsPlan(parseInt(e.target.value) || 1)}
          disabled={isSaving}
        />
        <span className="form-hint">
          Number of approvals needed before a plan can proceed
        </span>
      </div>

      <div className="form-group">
        <label htmlFor="approvals-task">Required Approvals for Tasks</label>
        <input
          id="approvals-task"
          type="number"
          min="1"
          max="10"
          value={requiredApprovalsTask}
          onChange={(e) => setRequiredApprovalsTask(parseInt(e.target.value) || 1)}
          disabled={isSaving}
        />
        <span className="form-hint">
          Number of approvals needed before a task can be merged
        </span>
      </div>

      <div className="form-group form-group-checkbox">
        <label className="checkbox-label">
          <input
            type="checkbox"
            checked={autoApprove}
            onChange={(e) => setAutoApprove(e.target.checked)}
            disabled={isSaving}
          />
          <span className="checkbox-text">Auto-approve main branch updates</span>
        </label>
        <span className="form-hint">
          Automatically approve plans when the main branch changes
        </span>
      </div>

      {hasChanges && (
        <button type="submit" className="btn btn-primary" disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save Settings'}
        </button>
      )}
    </form>
  )
}

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'settings'>('overview')
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false)
  const [editName, setEditName] = useState('')
  const [editGitUrl, setEditGitUrl] = useState('')
  const [editMainBranch, setEditMainBranch] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  useEffect(() => {
    const fetchProject = async () => {
      if (!projectId) return

      setIsLoading(true)
      setError(null)

      try {
        const data = await apiFetch<Project>(`/projects/${projectId}`)
        setProject(data)
        setEditName(data.name)
        setEditGitUrl(data.git_url)
        setEditMainBranch(data.main_branch)
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('Failed to load project')
        }
      } finally {
        setIsLoading(false)
      }
    }

    fetchProject()
  }, [projectId])

  const handleSaveProject = async (e: FormEvent) => {
    e.preventDefault()
    if (!projectId) return

    setEditError(null)
    setIsSaving(true)

    try {
      const updateData: ProjectUpdate = {}

      if (editName !== project?.name) updateData.name = editName.trim()
      if (editGitUrl !== project?.git_url) updateData.git_url = editGitUrl.trim()
      if (editMainBranch !== project?.main_branch)
        updateData.main_branch = editMainBranch.trim()

      if (Object.keys(updateData).length > 0) {
        const updated = await apiFetch<Project>(`/projects/${projectId}`, {
          method: 'PATCH',
          body: JSON.stringify(updateData),
        })
        setProject(updated)
        showSuccess('Project updated successfully')
      }

      setIsEditing(false)
    } catch (err) {
      if (err instanceof ApiError) {
        setEditError(err.message)
      } else {
        setEditError('Failed to update project')
      }
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveSettings = async (settings: ProjectSettingsUpdate) => {
    if (!projectId) return

    try {
      const updated = await apiFetch<ProjectSettings>(
        `/projects/${projectId}/settings`,
        {
          method: 'PATCH',
          body: JSON.stringify(settings),
        }
      )

      setProject((prev) => (prev ? { ...prev, settings: updated } : null))
      showSuccess('Settings saved successfully')
    } catch (err) {
      if (err instanceof ApiError) {
        throw err
      }
      throw new Error('Failed to save settings')
    }
  }

  const handleDelete = async () => {
    if (!projectId) return

    setIsDeleting(true)

    try {
      await apiFetch(`/projects/${projectId}`, {
        method: 'DELETE',
      })
      navigate('/projects')
    } catch (err) {
      setIsDeleting(false)
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to delete project')
      }
    }
  }

  const showSuccess = (message: string) => {
    setSuccessMessage(message)
    setTimeout(() => setSuccessMessage(null), 3000)
  }

  const cancelEdit = () => {
    setIsEditing(false)
    setEditError(null)
    if (project) {
      setEditName(project.name)
      setEditGitUrl(project.git_url)
      setEditMainBranch(project.main_branch)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (isLoading) {
    return <LoadingSpinner message="Loading project..." />
  }

  if (error && !project) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>{error}</p>
          <button className="btn btn-secondary" onClick={() => navigate('/projects')}>
            Back to Projects
          </button>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="page-content">
        <div className="error-state">
          <p>Project not found</p>
          <button className="btn btn-secondary" onClick={() => navigate('/projects')}>
            Back to Projects
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="page-content">
      {successMessage && (
        <div className="success-message">{successMessage}</div>
      )}

      <div className="project-detail-header">
        <div className="project-title-section">
          <svg
            className="project-icon-large"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
          </svg>
          <div>
            <h2>{project.name}</h2>
            <p className="project-git-url">{project.git_url}</p>
          </div>
        </div>

        <div className="project-actions">
          <Link to={`/projects/${projectId}/plans`} className="btn btn-secondary">
            <svg
              className="btn-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14,2 14,8 20,8" />
            </svg>
            Plans
          </Link>
          <Link to={`/projects/${projectId}/tasks`} className="btn btn-secondary">
            <svg
              className="btn-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M9 11l3 3L22 4" />
              <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
            </svg>
            Tasks
          </Link>
        </div>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'overview' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={`tab ${activeTab === 'settings' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('settings')}
        >
          Settings
        </button>
      </div>

      {activeTab === 'overview' && (
        <div className="tab-content">
          <div className="detail-section">
            <div className="section-header">
              <h3>Project Details</h3>
              {!isEditing && (
                <button
                  className="btn btn-ghost"
                  onClick={() => setIsEditing(true)}
                >
                  <svg
                    className="btn-icon"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
                    <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
                  </svg>
                  Edit
                </button>
              )}
            </div>

            {isEditing ? (
              <form className="edit-form" onSubmit={handleSaveProject}>
                {editError && <div className="error-message">{editError}</div>}

                <div className="form-group">
                  <label htmlFor="edit-name">Project Name</label>
                  <input
                    id="edit-name"
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    required
                    disabled={isSaving}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="edit-git-url">Git Repository URL</label>
                  <input
                    id="edit-git-url"
                    type="text"
                    value={editGitUrl}
                    onChange={(e) => setEditGitUrl(e.target.value)}
                    required
                    disabled={isSaving}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="edit-branch">Main Branch</label>
                  <input
                    id="edit-branch"
                    type="text"
                    value={editMainBranch}
                    onChange={(e) => setEditMainBranch(e.target.value)}
                    required
                    disabled={isSaving}
                  />
                </div>

                <div className="form-actions">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={cancelEdit}
                    disabled={isSaving}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={isSaving}
                  >
                    {isSaving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="detail-grid">
                <div className="detail-item">
                  <span className="detail-label">Name</span>
                  <span className="detail-value">{project.name}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Repository</span>
                  <span className="detail-value">{project.git_url}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Main Branch</span>
                  <span className="detail-value">{project.main_branch}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Created</span>
                  <span className="detail-value">{formatDate(project.created_at)}</span>
                </div>
                {project.updated_at && (
                  <div className="detail-item">
                    <span className="detail-label">Last Updated</span>
                    <span className="detail-value">
                      {formatDate(project.updated_at)}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'settings' && (
        <div className="tab-content">
          <div className="detail-section">
            <h3>Approval Settings</h3>
            <SettingsForm settings={project.settings} onSave={handleSaveSettings} />
          </div>

          <div className="detail-section danger-zone">
            <h3>Danger Zone</h3>
            <div className="danger-zone-content">
              <div className="danger-zone-text">
                <strong>Delete this project</strong>
                <p>
                  Once you delete a project, there is no going back. This will
                  permanently delete all associated plans and tasks.
                </p>
              </div>
              <button
                className="btn btn-danger"
                onClick={() => setIsDeleteModalOpen(true)}
              >
                Delete Project
              </button>
            </div>
          </div>
        </div>
      )}

      <DeleteConfirmModal
        isOpen={isDeleteModalOpen}
        projectName={project.name}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleDelete}
        isDeleting={isDeleting}
      />
    </div>
  )
}
