import axios from 'axios'
import type { Alert, AlertResponse, DetectionRule, Process, SystemStats } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Alerts API
export const alertsApi = {
  getAll: (params?: { limit?: number; offset?: number; severity?: string; acknowledged?: boolean }) =>
    client.get<AlertResponse>('/api/alerts', { params }),
  
  getById: (id: number) =>
    client.get<Alert>(`/api/alerts/${id}`),
  
  getRecent: (minutes: number = 60) =>
    client.get<Alert[]>(`/api/alerts/recent?minutes=${minutes}`),
  
  getStats: () =>
    client.get('/api/alerts/stats'),
  
  acknowledge: (id: number) =>
    client.post(`/api/alerts/${id}/acknowledge`),
  
  unacknowledge: (id: number) =>
    client.post(`/api/alerts/${id}/unacknowledge`),
  
  delete: (id: number) =>
    client.delete(`/api/alerts/${id}`),
  
  bulkAcknowledge: (ids: number[]) =>
    client.post('/api/alerts/bulk/acknowledge', ids),
}

// Processes API
export const processesApi = {
  getAll: (params?: { limit?: number; offset?: number; search?: string }) =>
    client.get<Process[]>('/api/processes', { params }),
  
  getById: (id: number) =>
    client.get<Process>(`/api/processes/${id}`),
  
  getRecent: (minutes: number = 5) =>
    client.get<Process[]>(`/api/processes/recent?minutes=${minutes}`),
  
  getStats: () =>
    client.get('/api/processes/stats'),
  
  getTree: (id: number) =>
    client.get<Process>(`/api/processes/${id}/tree`),
  
  getByParent: (parentName: string, limit?: number) =>
    client.get<Process[]>(`/api/processes/by-parent/${parentName}`, { params: { limit } }),
  
  delete: (id: number) =>
    client.delete(`/api/processes/${id}`),
}

// Detection API
export const detectionApi = {
  getRules: (params?: { enabled_only?: boolean; rule_type?: string }) =>
    client.get<{ total: number; rules: DetectionRule[] }>('/api/detection/rules', { params }),
  
  getRule: (id: string) =>
    client.get<{ rule: DetectionRule }>(`/api/detection/rules/${id}`),
  
  createRule: (rule: DetectionRule) =>
    client.post('/api/detection/rules', rule),
  
  updateRule: (id: string, rule: DetectionRule) =>
    client.put(`/api/detection/rules/${id}`, rule),
  
  toggleRule: (id: string, enabled: boolean) =>
    client.post(`/api/detection/rules/${id}/toggle`, { enabled }),
  
  deleteRule: (id: string) =>
    client.delete(`/api/detection/rules/${id}`),
  
  getStats: () =>
    client.get<SystemStats>('/api/detection/stats'),
  
  testProcess: (process: {
    process_name: string
    parent_name: string
    command_line: string
    process_id?: number
    parent_process_id?: number
  }) =>
    client.post('/api/detection/test', process),
  
  reloadRules: () =>
    client.post('/api/detection/reload'),
  
  exportRules: (filePath: string) =>
    client.post('/api/detection/export', { file_path: filePath }),
  
  importRules: (filePath: string) =>
    client.post('/api/detection/import', { file_path: filePath }),
}

// System API
export const systemApi = {
  getHealth: () =>
    client.get('/health'),
  
  getStats: () =>
    client.get<SystemStats>('/api/stats'),
  
  ingestEvent: (eventData: unknown) =>
    client.post('/api/ingest', eventData),
  
  simulateBatch: (count: number = 10, suspiciousRatio: number = 0.2) =>
    client.post(`/api/simulate/batch?count=${count}&suspicious_ratio=${suspiciousRatio}`),
  
  toggleSimulation: (enabled: boolean) =>
    client.post(`/api/simulation/toggle?enabled=${enabled}`),
}

export default client