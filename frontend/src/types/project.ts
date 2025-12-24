export interface ProjectSettings {
  required_approvals_plan: number
  required_approvals_task: number
  auto_approve_main_updates: boolean
  assigned_hats: string[]
}

export interface ProjectSettingsUpdate {
  required_approvals_plan?: number
  required_approvals_task?: number
  auto_approve_main_updates?: boolean
  assigned_hats?: string[]
}

export interface Project {
  id: string
  name: string
  git_url: string
  main_branch: string
  settings: ProjectSettings
  triage_connection_id: string | null
  created_at: string
  updated_at: string | null
}

export interface ProjectCreate {
  name: string
  git_url: string
  main_branch?: string
  settings?: Partial<ProjectSettings>
  triage_connection_id?: string
}

export interface ProjectUpdate {
  name?: string
  git_url?: string
  main_branch?: string
  triage_connection_id?: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  pages: number
}
