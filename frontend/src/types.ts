export type Role = "analyst" | "supervisor" | "admin"
export type Band = "low" | "medium" | "high"
type Json = Record<string, unknown>

export interface Page<T> {
  items: T[]
  total: number
}

export interface User {
  id: number
  email: string
  role: Role
  is_active: boolean
}

export interface Job {
  id: number
  kind: string
  status: "queued" | "running" | "done" | "failed"
  log: string
  error: string | null
  result: Json | null
}

export interface AuditEntry {
  id: number
  user_id: number | null
  action: string
  entity: string
  entity_id: string | null
  detail: Json | null
  created_at: string
}

export interface EvalRun {
  id: number
  kind: string
  name: string
  metrics: Json
  created_at: string
}

export interface OrderFilter {
  market?: string
  shipping_mode?: string
  band?: Band
  include_trained: boolean
  q?: string
}

export interface OrderRow {
  id: number
  order_id: number
  order_date: string
  market: string
  order_region: string
  shipping_mode: string
  customer_segment: string
  order_total: number
  block: string
  risk_score: number | null
  risk_band: Band | null
}

export interface Factor {
  feature: string
  value: unknown
  impact: number
}

export interface OrderDetail extends OrderRow {
  features: Json
  factors: Factor[] | null
  late: boolean | null
  model_version_id: number | null
}

export interface RiskSummary {
  total: number
  high: number
  medium: number
  low: number
  mean_score: number | null
  by_shipping_mode: Json[]
}

export interface OrderStats {
  total: number
  by_band: Record<string, number>
  by_market: Json[]
  by_shipping_mode: Json[]
  champion_version: number | null
}

export interface Incident {
  id: number
  tweet_id: string | null
  text: string
  event: string | null
  source: "pool" | "manual"
  status: "pool" | "classified" | "needs_review" | "reviewed"
  predicted_label: string | null
  confidence: number | null
  screening_score: number | null
  model_version_id: number | null
  reviewed_label: string | null
  reviewed_by: number | null
  reviewed_at: string | null
  review_source: "analyst" | "batch" | null
  created_at: string
}

export interface Classification {
  label: string
  confidence: number
  screening_score: number
  needs_review: boolean
  model_version_id: number | null
}

export interface IncidentStats {
  by_status: Record<string, number>
  by_label: Record<string, number>
  needs_review: number
  reviews_since_champion: number
}

export interface ModelVersion {
  id: number
  task: "risk" | "incident"
  version: number
  family: string
  artifact_path: string
  artifact_hash: string
  snapshot_hash: string | null
  git_commit: string | null
  metrics: Json
  gate: Json | null
  status: "candidate" | "champion" | "retired" | "rejected"
  promoted_at: string | null
  created_at: string
}

export interface Document {
  id: number
  code: string
  title: string
  origin: "public" | "team-authored"
  content_hash: string
  status: "processing" | "ready" | "failed"
  chunk_count: number
  created_at: string
}

export interface Chunk {
  citation_key: string
  document_title: string
  section: string | null
  text: string
  score: number
}

export interface SearchResult {
  chunks: Chunk[]
  evidence_gap: boolean
  best_score: number | null
}

export interface ActionRule {
  id: number
  code: string
  name: string
  description: string
  cost_usd: number
  approval_role: Role
  categories: string[]
  min_high_risk_orders: number
  requires_evidence: boolean
  is_active: boolean
  created_at: string
}

export interface RuleResult {
  rule_code: string
  name: string
  eligible: boolean
  reason: string
  approval_role: Role
  cost_usd: number
}

export interface Investigation {
  id: number
  incident_id: number
  scope: Json
  status: "running" | "awaiting_approval" | "reporting" | "completed" | "closed" | "failed"
  degraded: boolean
  created_at: string
}

export interface Step {
  id: number
  node: string
  status: "ok" | "error"
  output: Json | null
  error: string | null
  duration_ms: number
}

export interface Action {
  id: number
  investigation_id: number
  rule_code: string
  name: string
  eligible: boolean
  reason: string
  rank: number | null
  rationale: string | null
  decision: "pending" | "approved" | "rejected"
  decided_by: number | null
  decided_at: string | null
}

export interface InvestigationDetail extends Investigation {
  incident: Incident
  state: Json
  steps: Step[]
  actions: Action[]
  report: string | null
}

export interface ChatMessage {
  id: number
  session_id: string
  user_id: number
  role: "user" | "assistant"
  content: string
  tool_calls: Json[] | null
  citations: Json[] | null
  created_at: string
}

export interface ChatEvent {
  type: "tool" | "answer" | "error" | "done"
  name?: string
  content?: string
  citations?: Json[]
  degraded?: boolean
}
