import { useState } from 'react'
import { useStore } from '../store'
import { CardItem } from './CardItem'
import { AddCardModal } from './AddCardModal'
import type { Card } from '../api/client'

const COLUMNS: { id: Card['status']; label: string }[] = [
  { id: 'todo', label: 'Todo' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'review', label: 'Review' },
  { id: 'done', label: 'Done' },
]

export function KanbanBoard() {
  const { activeProjectId, cards } = useStore()
  const [showAdd, setShowAdd] = useState(false)
  if (!activeProjectId) return null
  const projectCards = cards[activeProjectId] || []

  return (
    <div className="flex gap-4 p-6 h-full overflow-x-auto">
      {COLUMNS.map(col => {
        const colCards = projectCards.filter(c => c.status === col.id)
        return (
          <div key={col.id} className="flex-shrink-0 w-64">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase text-gray-400 tracking-wider">{col.label}</span>
              <span className="text-xs bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full">{colCards.length}</span>
            </div>
            <div className="min-h-8">
              {colCards.map(card => <CardItem key={card.id} card={card} />)}
            </div>
            {col.id === 'todo' && (
              <button
                onClick={() => setShowAdd(true)}
                className="w-full mt-1 border border-dashed border-gray-700 rounded-lg py-2 text-xs text-gray-600 hover:text-gray-400 hover:border-gray-600 transition-colors"
              >
                + Add card
              </button>
            )}
          </div>
        )
      })}
      {showAdd && activeProjectId && (
        <AddCardModal projectId={activeProjectId} onClose={() => setShowAdd(false)} />
      )}
    </div>
  )
}
