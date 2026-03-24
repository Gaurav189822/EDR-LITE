import { AlertTriangle, ArrowLeft, Terminal } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { processesApi } from '../api/client'
import type { ProcessTreeNode } from '../types'

export default function ProcessTree() {
  const { id } = useParams<{ id: string }>()
  const [tree, setTree] = useState<ProcessTreeNode | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadTree = async () => {
      if (!id) return
      
      setIsLoading(true)
      try {
        const response = await processesApi.getTree(parseInt(id))
        setTree(response.data as unknown as ProcessTreeNode)
      } catch (err) {
        setError('Failed to load process tree')
        console.error('Error loading process tree:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadTree()
  }, [id])

  const renderNode = (node: ProcessTreeNode, depth: number = 0) => {
    const processName = node.process_name.split('\\').pop() || node.process_name
    
    return (
      <div key={node.id} style={{ marginLeft: depth * 24 }}>
        <div 
          className={`
            flex items-start gap-3 p-3 rounded-lg border mb-2
            ${node.is_suspicious 
              ? 'bg-red-950/20 border-red-500/30' 
              : 'bg-slate-850 border-slate-700'
            }
          `}
        >
          <div className={`
            p-2 rounded-lg
            ${node.is_suspicious ? 'bg-red-500/20 text-red-400' : 'bg-slate-700 text-slate-400'}
          `}>
            <Terminal className="w-4 h-4" />
          </div>
          
          <div className="flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-primary-400 font-medium">{processName}</span>
              <span className="text-slate-500 text-sm">PID: {node.process_id}</span>
              {node.is_suspicious && (
                <span className="badge badge-critical flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  Suspicious
                </span>
              )}
            </div>
            
            <div className="mt-1 p-2 bg-slate-900 rounded font-mono text-xs text-slate-300 break-all">
              {node.command_line}
            </div>
            
            <div className="text-xs text-slate-500 mt-1">
              {new Date(node.timestamp).toLocaleString()}
            </div>
          </div>
        </div>
        
        {node.children && node.children.length > 0 && (
          <div className="border-l-2 border-slate-700 ml-4 pl-2">
            {node.children.map(child => renderNode(child, 0))}
          </div>
        )}
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin w-8 h-8 border-2 border-primary-400 border-t-transparent rounded-full mx-auto" />
        <p className="text-slate-400 mt-4">Loading process tree...</p>
      </div>
    )
  }

  if (error || !tree) {
    return (
      <div className="card text-center py-12">
        <AlertTriangle className="w-16 h-16 mx-auto text-red-400 mb-4" />
        <h3 className="text-lg font-medium text-white mb-2">Error</h3>
        <p className="text-slate-400">{error || 'Process not found'}</p>
        <Link to="/processes" className="btn-primary mt-4 inline-block">
          Back to Processes
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/processes" className="p-2 hover:bg-slate-800 rounded-lg transition-colors">
          <ArrowLeft className="w-6 h-6 text-slate-400" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-white">Process Tree</h1>
          <p className="text-slate-400">
            Process ID: {tree.process_id} • {tree.process_name.split('\\').pop()}
          </p>
        </div>
      </div>

      {/* Tree */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">Execution Chain</h2>
        <div className="overflow-x-auto">
          {renderNode(tree)}
        </div>
      </div>
    </div>
  )
}