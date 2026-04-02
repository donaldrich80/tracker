import { useState } from 'react'
import { useStore } from '../store'
import { CardItem } from './CardItem'
import { AddCardModal } from './AddCardModal'
import type { Card } from '../api/client'

const GROUPS: Card['status'][] = ['in_progress', 'todo', 'review', 'blocked', 'done']
const LABELS: Record<Card['status'], string> = {
  in_progress: 'In Progress', todo: 'Todo', review: 'Review', blocked: 'Blocked', done: 'Done'
}

export function ListView() {
  const { activeProjectId, cards } = useStore()
  const [showAdd, setShowAdd] = useState(false)
  if (!activeProjectId) return null
  const projectCards = cards[activeProjectId] || []

  return (
    <div className="p-6 max-w-2xl">
      {GROUPS.map(status => {
        const grouped = projectCards.filter(c => c.status === status)
        if (grouped.length === 0) return null
        return (
          <div key={status} className="mb-6">
            <div className="text-xs font-bold uppercase text-gray-500 tracking-wider mb-2">{LABELS[status]}</div>
            {grouped.map(card => <CardItem key={card.id} card={card} compact />)}
          </div>
        )
      })}
      <button
        onClick={() => setShowAdd(true)}
        className="mt-2 border border-dashed border-gray-700 rounded-lg px-4 py-2 text-xs text-gray-600 hover:text-gray-400"
      >
        + Add card
      </button>
      {showAdd && activeProjectId && (
        <AddCardModal projectId={activeProjectId} onClose={() => setShowAdd(false)} />
      )}
    </div>
  )
}
