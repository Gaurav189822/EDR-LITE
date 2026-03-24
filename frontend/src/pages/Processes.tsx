import { FileCode, RefreshCw, Search, Terminal } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { processesApi } from '../api/client'
import ProcessCard from '../components/ProcessCard'
import { useWebSocket } from '../hooks/useWebSocket'
import type { Process } from '../types'

export default function Processes() {
  const [processes, setProcesses] = useState<Process[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [page, setPage] = useState(0)
  const limit = 20

  const loadProcesses = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await processesApi.getAll({
        limit,
        offset: page * limit,
        search: searchQuery || undefined,
      })
      setProcesses(response.data)
    } catch (error) {
      console.error('Error loading processes:', error)
    } finally {
      setIsLoading(false)
    }
  }, [searchQuery, page])

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: { type: string; data?: Process }) => {
    if (message.type === 'process_event' && message.data) {
      setProcesses(prev => [message.data as Process, ...prev].slice(0, limit))
    }
  }, [])

  useWebSocket({
    url: '/ws/events',
    onMessage: handleWebSocketMessage,
  })

  useEffect(() => {
    loadProcesses()
  }, [loadProcesses])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(0)
    loadProcesses()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <FileCode className="w-8 h-8 text-primary-400" />
          <div>
            <h1 className="text-2xl font-bold text-white">Process Monitor</h1>
            <p className="text-slate-400">Real-time process creation events</p>
          </div>
        </div>
        
        <button
          onClick={loadProcesses}
          disabled={isLoading}
          className="btn-primary flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="card">
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search processes, parents, or command lines..."
              className="input-field w-full pl-10"
            />
          </div>
          <button type="submit" className="btn-primary">
            Search
          </button>
        </div>
      </form>

      {/* Processes List */}
      <div className="space-y-3">
        {isLoading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto text-primary-400" />
            <p className="text-slate-400 mt-4">Loading processes...</p>
          </div>
        ) : processes.length === 0 ? (
          <div className="card text-center py-12">
            <Terminal className="w-16 h-16 mx-auto text-slate-500 mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No processes found</h3>
            <p className="text-slate-400">
              {searchQuery ? 'Try a different search term' : 'No process events recorded yet'}
            </p>
          </div>
        ) : (
          processes.map(process => (
            <ProcessCard key={process.id} process={process} />
          ))
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => setPage(p => Math.max(0, p - 1))}
          disabled={page === 0}
          className="btn-secondary disabled:opacity-50"
        >
          Previous
        </button>
        <span className="text-slate-400">Page {page + 1}</span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={processes.length < limit}
          className="btn-secondary disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  )
}