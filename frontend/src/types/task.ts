// Task status - matches backend PlanTaskStatus
export type TaskStatus =
  | 'backlog'
  | 'blocked'
  | 'coding'
  | 'review'
  | 'approved'
  | 'cicd'
  | 'merged'
  | 'closed'

// Enum version for easier usage
export enum TaskStatusEnum {
  BACKLOG = 'backlog',
  BLOCKED = 'blocked',
  CODING = 'coding',
  REVIEW = 'review',
  APPROVED = 'approved',
  CICD = 'cicd',
  MERGED = 'merged',
  CLOSED = 'closed',
}

// Main task interface
export interface Task {
  id: string
  project_id: string
  plan_id: string | null
  title: string
  description: string | null
  status: TaskStatus
  blocked_by: string[] // Task IDs that must complete first
  branch_name: string | null
  worktree_path: string | null
  version: number
  created_at: string
  updated_at: string | null
}

// Task with related entities for detail view
export interface TaskWithDetails extends Task {
  blocking_tasks: TaskSummary[] // Tasks that this task blocks
  blocked_by_tasks: TaskSummary[] // Tasks blocking this task
  plan: PlanSummary | null
  reviews: ReviewSummary[]
}

// Summary for lists and references
export interface TaskSummary {
  id: string
  title: string
  status: TaskStatus
}

// Plan summary for task detail
export interface PlanSummary {
  id: string
  title: string
  status: string
}

// Review summary
export interface ReviewSummary {
  id: string
  reviewer_id: string
  decision: 'approved' | 'request_changes'
  comment: string | null
  created_at: string
}

// Request to update a task
export interface TaskUpdate {
  title?: string
  description?: string | null
  status?: TaskStatus
}

// Status filter options for the dropdown
export const TASK_STATUS_OPTIONS: { value: TaskStatus | ''; label: string }[] = [
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
export const TASK_STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; color: string; bgColor: string; description: string }
> = {
  backlog: {
    label: 'Backlog',
    color: '#6b7280',
    bgColor: '#f3f4f6',
    description: 'Not yet started',
  },
  blocked: {
    label: 'Blocked',
    color: '#dc2626',
    bgColor: '#fef2f2',
    description: 'Waiting on other tasks',
  },
  coding: {
    label: 'Coding',
    color: '#2563eb',
    bgColor: '#eff6ff',
    description: 'In active development',
  },
  review: {
    label: 'Review',
    color: '#d97706',
    bgColor: '#fffbeb',
    description: 'Awaiting code review',
  },
  approved: {
    label: 'Approved',
    color: '#059669',
    bgColor: '#ecfdf5',
    description: 'Review passed',
  },
  cicd: {
    label: 'CI/CD',
    color: '#7c3aed',
    bgColor: '#f5f3ff',
    description: 'Running pipeline',
  },
  merged: {
    label: 'Merged',
    color: '#0891b2',
    bgColor: '#ecfeff',
    description: 'Merged to main',
  },
  closed: {
    label: 'Closed',
    color: '#374151',
    bgColor: '#f9fafb',
    description: 'Completed or cancelled',
  },
}

// Helper to get all tasks that can be worked on
export function isWorkableStatus(status: TaskStatus): boolean {
  return status === 'backlog' || status === 'coding'
}

// Helper to check if status indicates completion
export function isCompletedStatus(status: TaskStatus): boolean {
  return status === 'merged' || status === 'closed'
}
