// Plan status enum - matches backend PlanTaskStatus
export type PlanStatus =
  | 'backlog'
  | 'blocked'
  | 'coding'
  | 'review'
  | 'approved'
  | 'cicd'
  | 'merged'
  | 'closed'

// Enum version for easier usage with switch statements
export enum PlanTaskStatus {
  BACKLOG = 'backlog',
  BLOCKED = 'blocked',
  CODING = 'coding',
  REVIEW = 'review',
  APPROVED = 'approved',
  CICD = 'cicd',
  MERGED = 'merged',
  CLOSED = 'closed',
}

// Processing status for AI-generated content
export type ProcessingStatusType = 'pending' | 'generating' | 'completed' | 'failed'

// Enum version for easier usage
export enum ProcessingStatus {
  PENDING = 'pending',
  GENERATING = 'generating',
  COMPLETED = 'completed',
  FAILED = 'failed',
}

// Base plan interface
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

// Summary interfaces for related entities
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

// Plan with all related entities
export interface PlanWithDetails extends Plan {
  tasks: TaskSummary[]
  reviews: ReviewSummary[]
  threads: ThreadSummary[]
}

// Request to create a plan
export interface PlanCreate {
  title: string
  content?: string | null
  parent_task_id?: string | null
}

// Request to update a plan
export interface PlanUpdate {
  title?: string
  content?: string | null
}

// Request to generate plan content
export interface PlanGenerateRequest {
  context?: string | null
}

// Response from generation status endpoint
export interface PlanGenerationStatus {
  plan_id: string
  processing_status: ProcessingStatus | null
  processing_error: string | null
  content: string | null
}

// Request to spawn tasks from a plan
export interface SpawnTasksRequest {
  // No additional parameters needed
}

// Summary of a spawned task
export interface SpawnedTaskSummary {
  id: string
  title: string
  description: string | null
  blocked_by: string[]
}

// Response from spawning tasks
export interface SpawnTasksResponse {
  plan_id: string
  tasks_created: number
  tasks: SpawnedTaskSummary[]
}

// Status response for task spawning
export interface SpawnTasksStatus {
  plan_id: string
  processing_status: ProcessingStatus | null
  processing_error: string | null
  tasks_created: number | null
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
  [ProcessingStatus.PENDING]: { label: 'Pending', color: '#6b7280', bgColor: '#f3f4f6' },
  [ProcessingStatus.GENERATING]: { label: 'Generating...', color: '#2563eb', bgColor: '#eff6ff' },
  [ProcessingStatus.COMPLETED]: { label: 'Generated', color: '#059669', bgColor: '#ecfdf5' },
  [ProcessingStatus.FAILED]: { label: 'Failed', color: '#dc2626', bgColor: '#fef2f2' },
}

// Helper type for display purposes (enum-based labels)
export const PlanTaskStatusLabels: Record<PlanTaskStatus, string> = {
  [PlanTaskStatus.BACKLOG]: 'Backlog',
  [PlanTaskStatus.BLOCKED]: 'Blocked',
  [PlanTaskStatus.CODING]: 'Coding',
  [PlanTaskStatus.REVIEW]: 'Review',
  [PlanTaskStatus.APPROVED]: 'Approved',
  [PlanTaskStatus.CICD]: 'CI/CD',
  [PlanTaskStatus.MERGED]: 'Merged',
  [PlanTaskStatus.CLOSED]: 'Closed',
}

export const ProcessingStatusLabels: Record<ProcessingStatus, string> = {
  [ProcessingStatus.PENDING]: 'Pending',
  [ProcessingStatus.GENERATING]: 'Generating...',
  [ProcessingStatus.COMPLETED]: 'Completed',
  [ProcessingStatus.FAILED]: 'Failed',
}
