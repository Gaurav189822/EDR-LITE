import { Edit2, Play, Plus, RefreshCw, Settings, ToggleLeft, ToggleRight, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { detectionApi } from '../api/client'
import type { DetectionRule } from '../types'

export default function DetectionRules() {
  const [rules, setRules] = useState<DetectionRule[]>([])
  const [stats, setStats] = useState<{ by_type: Record<string, number>; by_severity: Record<string, number> } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingRule, setEditingRule] = useState<DetectionRule | null>(null)
  const [testResult, setTestResult] = useState<unknown>(null)

  const loadRules = useCallback(async () => {
    setIsLoading(true)
    try {
      const [rulesRes, statsRes] = await Promise.all([
        detectionApi.getRules(),
        detectionApi.getStats(),
      ])
      setRules(rulesRes.data.rules)
      setStats(statsRes.data.rules)
    } catch (error) {
      console.error('Error loading rules:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRules()
  }, [loadRules])

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await detectionApi.toggleRule(id, !enabled)
      setRules(prev => 
        prev.map(r => r.id === id ? { ...r, enabled: !enabled } : r)
      )
    } catch (error) {
      console.error('Error toggling rule:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this rule?')) return
    
    try {
      await detectionApi.deleteRule(id)
      setRules(prev => prev.filter(r => r.id !== id))
    } catch (error) {
      console.error('Error deleting rule:', error)
    }
  }

  const handleTestRule = async () => {
    try {
      const result = await detectionApi.testProcess({
        process_name: 'cmd.exe',
        parent_name: 'outlook.exe',
        command_line: 'cmd.exe /c whoami',
      })
      setTestResult(result.data)
    } catch (error) {
      console.error('Error testing rule:', error)
    }
  }

  const getRuleTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      parent_child: 'Parent-Child',
      command_line: 'Command Line',
      frequency: 'Frequency',
      behavior: 'Behavior',
      anomaly: 'Anomaly',
    }
    return labels[type] || type
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <Settings className="w-8 h-8 text-primary-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Detection Rules</h1>
            <p className="text-slate-400">
              {rules.filter(r => r.enabled).length} of {rules.length} rules active
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={handleTestRule}
            className="btn-secondary flex items-center gap-2"
          >
            <Play className="w-4 h-4" />
            Test Rule
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Rule
          </button>
          <button
            onClick={loadRules}
            disabled={isLoading}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Object.entries(stats.by_severity).map(([severity, count]) => (
            <div key={severity} className="card text-center">
              <p className="text-2xl font-bold text-white">{count}</p>
              <p className="text-sm text-slate-400 capitalize">{severity} Severity</p>
            </div>
          ))}
        </div>
      )}

      {/* Rules List */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-primary-400" />
            <p className="text-slate-400 mt-4">Loading rules...</p>
          </div>
        ) : rules.length === 0 ? (
          <div className="card text-center py-12">
            <Settings className="w-16 h-16 mx-auto text-slate-500 mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No rules found</h3>
            <p className="text-slate-400">Create your first detection rule</p>
          </div>
        ) : (
          rules.map(rule => (
            <div
              key={rule.id}
              className={`
                card flex items-center justify-between
                ${!rule.enabled ? 'opacity-60' : ''}
              `}
            >
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="font-semibold text-white">{rule.name}</h3>
                  <span className={`badge badge-${rule.severity}`}>
                    {rule.severity}
                  </span>
                  <span className="text-xs bg-slate-700 text-slate-300 px-2 py-1 rounded">
                    {getRuleTypeLabel(rule.rule_type)}
                  </span>
                  {rule.times_triggered !== undefined && rule.times_triggered > 0 && (
                    <span className="text-xs text-slate-400">
                      Triggered {rule.times_triggered} times
                    </span>
                  )}
                </div>
                <p className="text-slate-400 text-sm">{rule.description}</p>
                <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                  {rule.parent_process && (
                    <span>Parent: {rule.parent_process}</span>
                  )}
                  {rule.child_process && (
                    <span>Child: {rule.child_process}</span>
                  )}
                  <span>Risk Score: {rule.risk_score}</span>
                </div>
              </div>

              <div className="flex items-center gap-2 ml-4">
                <button
                  onClick={() => handleToggle(rule.id!, rule.enabled)}
                  className={`p-2 rounded-lg transition-colors ${
                    rule.enabled 
                      ? 'text-green-400 hover:bg-green-400/10' 
                      : 'text-slate-500 hover:bg-slate-700'
                  }`}
                  title={rule.enabled ? 'Disable' : 'Enable'}
                >
                  {rule.enabled ? (
                    <ToggleRight className="w-6 h-6" />
                  ) : (
                    <ToggleLeft className="w-6 h-6" />
                  )}
                </button>
                
                <button
                  onClick={() => setEditingRule(rule)}
                  className="p-2 text-slate-400 hover:text-primary-400 hover:bg-primary-400/10 rounded-lg transition-colors"
                  title="Edit"
                >
                  <Edit2 className="w-5 h-5" />
                </button>
                
                <button
                  onClick={() => handleDelete(rule.id!)}
                  className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
                  title="Delete"
                >
                  <Trash2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Test Result Modal */}
      {testResult && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-white mb-4">Test Result</h3>
            <pre className="bg-slate-950 p-4 rounded-lg text-sm text-slate-300 overflow-x-auto">
              {JSON.stringify(testResult, null, 2)}
            </pre>
            <button
              onClick={() => setTestResult(null)}
              className="btn-primary mt-4"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Create/Edit Modal Placeholder */}
      {(showCreateModal || editingRule) && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 rounded-lg p-6 max-w-lg w-full">
            <h3 className="text-lg font-semibold text-white mb-4">
              {editingRule ? 'Edit Rule' : 'Create Rule'}
            </h3>
            <p className="text-slate-400 mb-4">
              Rule editing UI would be implemented here with form fields for all rule properties.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowCreateModal(false)
                  setEditingRule(null)
                }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowCreateModal(false)
                  setEditingRule(null)
                }}
                className="btn-primary"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}