import { Wifi, WifiOff } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'

export default function WebSocketStatus() {
  const { isConnected } = useWebSocket({
    url: '/ws/alerts',
  })

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-slate-800 rounded-lg">
      {isConnected ? (
        <>
          <Wifi className="w-4 h-4 text-green-400" />
          <span className="text-sm text-green-400">Live</span>
        </>
      ) : (
        <>
          <WifiOff className="w-4 h-4 text-red-400" />
          <span className="text-sm text-red-400">Offline</span>
        </>
      )}
    </div>
  )
}