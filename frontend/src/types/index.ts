export interface Alert {
  id: number
  process_id: number
  rule_triggered: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  description: string
  risk_score: number
  details?: Record<string, unknown>
  timestamp: string
  acknowledged: boolean
}

export interface AlertResponse {
  total: number
  alerts: Alert[]
  severity_counts: Record<string, number>
}

export interface Process {
  id: number
  process_name: string
  parent_name: string
  command_line: string
  process_id: number
  parent_process_id: number
  timestamp: string
  user?: string
  computer?: string
  created_at: string
}

export interface ProcessTreeNode {
  id: number
  process_name: string
  process_id: number
  parent_process_id: number
  command_line: string
  timestamp: string
  children: ProcessTreeNode[]
  is_suspicious: boolean
  severity?: string
}

export interface DetectionRule {
  id?: string
  name: string
  rule_type: 'parent_child' | 'command_line' | 'frequency' | 'behavior' | 'anomaly'
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  enabled: boolean
  parent_process?: string
  child_process?: string
  command_line_pattern?: string
  command_line_contains?: string[]
  max_events_per_minute?: number
  time_window_minutes?: number
  risk_score: number
  times_triggered?: number
}

export interface SystemStats {
  engine: {
    events_analyzed: number
    alerts_generated: number
    uptime_seconds: number
    rules_loaded: number
    rules_enabled: number
  }
  rules: {
    total_rules: number
    enabled_rules: number
    disabled_rules: number
    by_type: Record<string, number>
    by_severity: Record<string, number>
  }
}

export interface WebSocketMessage {
  type: 'connection' | 'alert' | 'process_event' | 'heartbeat' | 'stats_update' | 'error'
  data?: unknown
  timestamp: string
  message?: string
}