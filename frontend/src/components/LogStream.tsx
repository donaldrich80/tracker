import { useEffect, useRef } from 'react'
import type { CardEvent } from '../api/client'

interface Props { events: CardEvent[] }

export function LogStream({ events }: Props) {
  const logs = events.filter(e => e.type === 'log')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs.length])

  if (logs.length === 0) {
    return <div className="text-xs text-gray-600 italic">No log entries yet.</div>
  }

  return (
    <div className="bg-gray-950 rounded-lg p-3 font-mono text-xs overflow-auto max-h-48 space-y-0.5">
      {logs.map(e => (
        <div key={e.id} className="flex gap-2">
          <span className="text-gray-600 shrink-0">
            {e.created_at ? new Date(e.created_at).toLocaleTimeString() : ''}
          </span>
          <span className="text-gray-300 break-all">{e.body}</span>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  )
}
