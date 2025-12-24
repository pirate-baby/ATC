// Session types for coding session management

// Session status enum
export type SessionStatus = 'active' | 'ended'

// Session target type (matches backend)
export type SessionTargetType = 'plan' | 'task'

// Session summary returned with task details
export interface SessionSummary {
  id: string
  status: string
  started_at: string
}

// Response from POST /tasks/{id}/start-session
export interface StartSessionResponse {
  task_id: string
  branch_name: string
  worktree_path: string
  status: string // Task status after starting (should be 'coding')
  session_started_at: string
}

// Extended session info for display
export interface SessionDisplayInfo {
  isActive: boolean
  branchName: string | null
  worktreePath: string | null
  startedAt: string | null
  endedAt: string | null
}
