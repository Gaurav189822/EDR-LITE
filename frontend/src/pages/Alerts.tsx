import { AlertTriangle, CheckSquare, Filter, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { alertsApi } from '../api/client'
import AlertCard from '../components/AlertCard'
import { useWebSocket } from '../hooks/useWebSocket'
import type { Alert } from '../types'

type SeverityFilter = 'all' | 'critical' | 'high' | 'medium' | 'low'
type StatusFilter = 'all' | 'acknowledged' | 'unacknowledged'

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [selectedAlerts, setSelectedAlerts] = useState<Set<number>>(new Set())
  const [page, setPage] = useState(0)
  const limit = 20

  const loadAlerts = useCallback(async () => {
    setIsLoading(true)
    try {
      const params: { limit: number; offset: number; severity?: string; acknowledged?: boolean } = {
        limit,
        offset: page * limit,
      }
      
      if (severityFilter !== 'all') {
        params.severity = severityFilter
      }
      
      if (statusFilter !== 'all') {
        params.acknowledged = statusFilter === 'acknowledged'
      }
      
      const response = await alertsApi.getAll(params)
      setAlerts(response.data.alerts)
      setTotal(response.data.total)
    } catch (error) {
      console.error('Error loading alerts:', error)
    } finally {
      setIsLoading(false)
    }
  }, [severityFilter, statusFilter, page])

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: { type: string; data?: Alert }) => {
    if (message.type === 'alert' && message.data) {
      setAlerts(prev => [message.data as Alert, ...prev])
      setTotal(prev => prev + 1)
    }
  }, [])

  useWebSocket({
    url: '/ws/alerts',
    onMessage: handleWebSocketMessage,
  })

  useEffect(() => {
    loadAlerts()
  }, [loadAlerts])

  const handleAcknowledge = async (id: number) => {
    try {
      await alertsApi.acknowledge(id)
      setAlerts(prev => 
        prev.map(a => a.id === id ? { ...a, acknowledged: true } : a)
      )
    } catch (error) {
      console.error('Error acknowledging alert:', error)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this alert?')) return
    
    try {
      await alertsApi.delete(id)
      setAlerts(prev => prev.filter(a => a.id !== id))
      setTotal(prev => prev - 1)
    } catch (error) {
      console.error('Error deleting alert:', error)
    }
  }

  const handleBulkAcknowledge = async () => {
    if (selectedAlerts.size === 0) return
    
    try {
      await alertsApi.bulkAcknowledge(Array.from(selectedAlerts))
      setAlerts(prev => 
        prev.map(a => selectedAlerts.has(a.id) ? { ...a, acknowledged: true } : a)
      )
      setSelectedAlerts(new Set())
    } catch (error) {
      console.error('Error bulk acknowledging alerts:', error)
    }
  }

  const toggleSelection = (id: number) => {
    setSelectedAlerts(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-8 h-8 text-yellow-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Security Alerts</h1>
            <p className="text-slate-400">{total} total alerts</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {selectedAlerts.size > 0 && (
            <button
              onClick={handleBulkAcknowledge}
              className="btn-secondary flex items-center gap-2"
            >
              <CheckSquare className="w-4 h-4" />
              Acknowledge ({selectedAlerts.size})
            </button>
          )}
          <button
            onClick={loadAlerts}
            disabled={isLoading}
            className="btn-primary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-5 h-5 text-slate-400" />
          <span className="font-medium text-white">Filters</span>
        </div>
        
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Severity</label>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value as SeverityFilter)}
              className="input-field"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm text-slate-400 mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
              className="input-field"
            >
              <option value="all">All Status</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="unacknowledged">Unacknowledged</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-primary-400" />
            <p className="text-slate-400 mt-4">Loading alerts...</p>
          </div>
        ) : alerts.length === 0 ? (
          <div className="card text-center py-12">
            <AlertTriangle className="w-16 h-16 mx-auto text-slate-500 mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No alerts found</h3>
            <p className="text-slate-400">Try adjusting your filters</p>
          </div>
        ) : (
          alerts.map(alert => (
            <div key={alert.id} className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={selectedAlerts.has(alert.id)}
                onChange={() => toggleSelection(alert.id)}
                className="mt-4 w-5 h-5 rounded border-slate-600 bg-slate-800 text-primary-500 focus:ring-primary-500"
              />
              <div className="flex-1">
                <AlertCard
                  alert={alert}
                  onAcknowledge={handleAcknowledge}
                  onDelete={handleDelete}
                />
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {total > limit && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            className="btn-secondary disabled:opacity-50"
          >
            Previous
          </button>
          <span className="text-slate-400">
            Page {page + 1} of {Math.ceil(total / limit)}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={(page + 1) * limit >= total}
            className="btn-secondary disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}