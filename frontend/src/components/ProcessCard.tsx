import { format } from 'date-fns'
import { ArrowRight, Clock, Terminal } from 'lucide-react'
import type { Process } from '../types'

interface ProcessCardProps {
  process: Process
  isSuspicious?: boolean
}

export default function ProcessCard({ process, isSuspicious = false }: ProcessCardProps) {
  const processName = process.process_name.split('\\').pop() || process.process_name
  const parentName = process.parent_name.split('\\').pop() || process.parent_name

  return (
    <div className={`
      rounded-lg p-4 border transition-all
      ${isSuspicious 
        ? 'bg-red-950/20 border-red-500/30' 
        : 'bg-slate-850 border-slate-700 hover:border-slate-600'
      }
    `}>
      <div className="flex items-start gap-3">
        <div className={`
          p-2 rounded-lg
          ${isSuspicious ? 'bg-red-500/20 text-red-400' : 'bg-slate-700 text-slate-400'}
        `}>
          <Terminal className="w-5 h-5" />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-mono text-primary-400 font-medium">{processName}</span>
            <ArrowRight className="w-4 h-4 text-slate-500" />
            <span className="font-mono text-slate-400">{parentName}</span>
            {isSuspicious && (
              <span className="badge badge-critical">Suspicious</span>
            )}
          </div>
          
          <div className="mt-2 p-2 bg-slate-900 rounded font-mono text-sm text-slate-300 break-all">
            {process.command_line}
          </div>
          
          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {format(new Date(process.timestamp), 'MMM d, HH:mm:ss')}
            </span>
            <span>PID: {process.process_id}</span>
            <span>PPID: {process.parent_process_id}</span>
            {process.user && <span>User: {process.user}</span>}
          </div>
        </div>
      </div>
    </div>
  )
}