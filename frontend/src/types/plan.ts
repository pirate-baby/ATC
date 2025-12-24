// Plan status enum matching backend PlanTaskStatus
export type PlanStatus =
  | 'backlog'
  | 'blocked'
  | 'coding'
  | 'review'
  | 'approved'
  | 'cicd'
  | 'merged'
  | 'closed'

// Processing status for AI-generated content
export type ProcessingStatus = 'pending' | 'generating' | 'completed' | 'failed'

export interface Plan {
  id: string
  project_id: string
  title: string
  content: string | null
  status: PlanStatus
  parent_task_id: string | null
  version: number
  processing_status: ProcessingStatus | null
  processing_error: string | null
  created_by: string | null
  created_at: string
  updated_at: string | null
}

export interface TaskSummary {
  id: string
  title: string
  status: PlanStatus
}

export interface ReviewSummary {
  id: string
  reviewer_id: string
  decision: string
  created_at: string
}

export interface ThreadSummary {
  id: string
  status: string
  comment_count: number
}

export interface PlanWithDetails extends Plan {
  tasks: TaskSummary[]
  reviews: ReviewSummary[]
  threads: ThreadSummary[]
}

export interface PlanCreate {
  title: string
  content?: string | null
  parent_task_id?: string | null
}

export interface PlanUpdate {
  title?: string
  content?: string | null
}

// For the status filter dropdown
export const PLAN_STATUS_OPTIONS: { value: PlanStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'backlog', label: 'Backlog' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'coding', label: 'Coding' },
  { value: 'review', label: 'Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'cicd', label: 'CI/CD' },
  { value: 'merged', label: 'Merged' },
  { value: 'closed', label: 'Closed' },
]

// Status display configuration
export const PLAN_STATUS_CONFIG: Record<
  PlanStatus,
  { label: string; color: string; bgColor: string }
> = {
  backlog: { label: 'Backlog', color: '#6b7280', bgColor: '#f3f4f6' },
  blocked: { label: 'Blocked', color: '#dc2626', bgColor: '#fef2f2' },
  coding: { label: 'Coding', color: '#2563eb', bgColor: '#eff6ff' },
  review: { label: 'Review', color: '#d97706', bgColor: '#fffbeb' },
  approved: { label: 'Approved', color: '#059669', bgColor: '#ecfdf5' },
  cicd: { label: 'CI/CD', color: '#7c3aed', bgColor: '#f5f3ff' },
  merged: { label: 'Merged', color: '#0891b2', bgColor: '#ecfeff' },
  closed: { label: 'Closed', color: '#374151', bgColor: '#f9fafb' },
}

// Processing status display configuration
export const PROCESSING_STATUS_CONFIG: Record<
  ProcessingStatus,
  { label: string; color: string; bgColor: string }
> = {
  pending: { label: 'Pending', color: '#6b7280', bgColor: '#f3f4f6' },
  generating: { label: 'Generating...', color: '#2563eb', bgColor: '#eff6ff' },
  completed: { label: 'Generated', color: '#059669', bgColor: '#ecfdf5' },
  failed: { label: 'Failed', color: '#dc2626', bgColor: '#fef2f2' },
}
