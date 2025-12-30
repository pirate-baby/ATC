/**
 * Types for Claude subscription token pooling system.
 */

export type ClaudeTokenStatus = 'active' | 'invalid' | 'rate_limited' | 'expired'

export interface ClaudeToken {
  id: string
  user_id: string
  name: string
  status: ClaudeTokenStatus
  token_preview: string
  request_count: number
  last_used_at: string | null
  rate_limit_reset_at: string | null
  last_error: string | null
  created_at: string
  updated_at: string | null
}

export interface ClaudeTokenCreate {
  name: string
  token: string
}

export interface ClaudeTokenUpdate {
  name?: string
  token?: string
}

export type PoolHealth = 'healthy' | 'limited' | 'exhausted'

export interface TokenPoolStatus {
  total_contributors: number
  active_tokens: number
  rate_limited_tokens: number
  invalid_tokens: number
  pool_health: PoolHealth
  total_requests_served: number
  next_available_at: string | null
}

export interface UsageDistribution {
  bucket: string
  count: number
}

export interface TokenPoolStats {
  status: TokenPoolStatus
  usage_distribution: UsageDistribution[]
  fairness_score: number
}

export interface TokenValidationResult {
  valid: boolean
  error: string | null
  account_type: string | null
}
