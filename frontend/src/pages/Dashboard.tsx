import {
    Activity,
    AlertTriangle,
    CheckCircle,
    FileCode,
    RefreshCw,
    Settings,
    ShieldAlert
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { alertsApi, processesApi, systemApi } from '../api/client'
import AlertCard from '../components/AlertCard'
import ProcessCard from '../components/ProcessCard'
import StatCard from '../components/StatCard'
import { useWebSocket } from '../hooks/useWebSocket'
import type { Alert, Process, SystemStats } from '../types'

export default function Dashboard() {
  const [stats, setStats] = useState<SystemStats | null>(null)
  const [recentAlerts, setRecentAlerts] = useState<Alert[]>([])
  const [recentProcesses, setRecentProcesses] = useState<Process[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const loadData = useCallback(async () => {
    setIsLoading(true)
    try {
      const [statsRes, alertsRes, processesRes] = await Promise.all([
        systemApi.getStats(),
        alertsApi.getAll({ limit: 5 }),
        processesApi.getRecent(5),
      ])

      setStats(statsRes.data)
      setRecentAlerts(alertsRes.data.alerts)
      setRecentProcesses(processesRes.data)
      setLastUpdate(new Date())
    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: { type: string; data?: Alert | Process }) => {
    if (message.type === 'alert' && message.data) {
      setRecentAlerts(prev => [message.data as Alert, ...prev].slice(0, 10))
    } else if (message.type === 'process_event' && message.data) {
      setRecentProcesses(prev => [message.data as Process, ...prev].slice(0, 10))
    }
  }, [])

  // Setup WebSocket
  useWebSocket({
    url: '/ws/alerts',
    onMessage: handleWebSocketMessage,
  })

  // Initial load
  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [loadData])

  const handleAcknowledge = async (id: number) => {
    try {
      await alertsApi.acknowledge(id)
      setRecentAlerts(prev => 
        prev.map(a => a.id === id ? { ...a, acknowledged: true } : a)
      )
    } catch (error) {
      console.error('Error acknowledging alert:', error)
    }
  }

  const handleSimulate = async () => {
    try {
      await systemApi.simulateBatch(5, 0.3)
      loadData()
    } catch (error) {
      console.error('Error simulating events:', error)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-slate-400">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleSimulate}
            className="btn-secondary flex items-center gap-2"
          >
            <Activity className="w-4 h-4" />
            Simulate Events
          </button>
          <button
            onClick={loadData}
            disabled={isLoading}
            className="btn-primary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Alerts"
          value={stats?.engine?.alerts_generated || 0}
          icon={ShieldAlert}
          color="red"
        />
        <StatCard
          title="High Severity"
          value={stats?.rules?.by_severity?.high || 0}
          icon={AlertTriangle}
          color="yellow"
        />
        <StatCard
          title="Processes"
          value={stats?.engine?.events_analyzed || 0}
          icon={FileCode}
          color="blue"
        />
        <StatCard
          title="Active Rules"
          value={stats?.engine?.rules_enabled || 0}
          icon={Settings}
          color="purple"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              Recent Alerts
            </h2>
            <a href="/alerts" className="text-primary-400 hover:text-primary-300 text-sm">
              View All →
            </a>
          </div>
          
          <div className="space-y-3 max-h-[500px] overflow-y-auto scrollbar-thin">
            {recentAlerts.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-400" />
                <p>No alerts found</p>
                <p className="text-sm">System is secure</p>
              </div>
            ) : (
              recentAlerts.map(alert => (
                <AlertCard
                  key={alert.id}
                  alert={alert}
                  onAcknowledge={handleAcknowledge}
                />
              ))
            )}
          </div>
        </div>

        {/* Recent Processes */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary-400" />
              Recent Processes
            </h2>
            <a href="/processes" className="text-primary-400 hover:text-primary-300 text-sm">
              View All →
            </a>
          </div>
          
          <div className="space-y-3 max-h-[500px] overflow-y-auto scrollbar-thin">
            {recentProcesses.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Activity className="w-12 h-12 mx-auto mb-3 text-slate-400" />
                <p>No processes found</p>
              </div>
            ) : (
              recentProcesses.map(process => (
                <ProcessCard
                  key={process.id}
                  process={process}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}