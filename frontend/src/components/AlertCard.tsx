import { format } from 'date-fns'
import { AlertTriangle, Check, Clock, X } from 'lucide-react'
import type { Alert } from '../types'

interface AlertCardProps {
  alert: Alert
  onAcknowledge?: (id: number) => void
  onDelete?: (id: number) => void
}

const severityConfig = {
  critical: { icon: AlertTriangle, className: 'alert-critical', badge: 'badge-critical' },
  high: { icon: AlertTriangle, className: 'alert-high', badge: 'badge-high' },
  medium: { icon: AlertTriangle, className: 'alert-medium', badge: 'badge-medium' },
  low: { icon: AlertTriangle, className: 'alert-low', badge: 'badge-low' },
}

export default function AlertCard({ alert, onAcknowledge, onDelete }: AlertCardProps) {
  const config = severityConfig[alert.severity]
  const Icon = config.icon

  return (
    <div className={`rounded-lg p-4 ${config.className} animate-slide-in`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <Icon className={`w-5 h-5 text-severity-${alert.severity}`} />
            <span className={`badge ${config.badge}`}>{alert.severity}</span>
            <span className="text-slate-400 text-sm">{alert.rule_triggered}</span>
          </div>
          
          <p className="text-slate-100 mb-2">{alert.description}</p>
          
          <div className="flex items-center gap-4 text-sm text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              {format(new Date(alert.timestamp), 'MMM d, HH:mm:ss')}
            </span>
            <span>Risk Score: {alert.risk_score}</span>
            {alert.acknowledged && (
              <span className="text-green-400">Acknowledged</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 ml-4">
          {!alert.acknowledged && onAcknowledge && (
            <button
              onClick={() => onAcknowledge(alert.id)}
              className="p-2 text-slate-400 hover:text-green-400 hover:bg-green-400/10 rounded-lg transition-colors"
              title="Acknowledge"
            >
              <Check className="w-5 h-5" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(alert.id)}
              className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-colors"
              title="Delete"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}