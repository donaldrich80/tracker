import { useStore } from '../store'
import { api } from '../api/client'
import type { Card } from '../api/client'
import { LogStream } from './LogStream'

const STATUS_OPTIONS = ['todo', 'in_progress', 'review', 'done', 'blocked'] as const
const PRIORITY_OPTIONS = ['low', 'medium', 'high'] as const

export function CardDetail() {
  const { activeCardId, cards, events, upsertCard, setActiveCard, activeProjectId } = useStore()
  const projectCards = activeProjectId ? (cards[activeProjectId] || []) : []
  const card = projectCards.find(c => c.id === activeCardId)
  const cardEvents = activeCardId ? (events[activeCardId] || []) : []

  if (!card) return null
  const milestones = cardEvents.filter(e => e.type === 'milestone')

  const updateStatus = async (status: string) => {
    const updated = await api.cards.update(card.id, { status: status as Card['status'] })
    upsertCard(updated)
  }

  const updatePriority = async (priority: string) => {
    const updated = await api.cards.update(card.id, { priority: priority as Card['priority'] })
    upsertCard(updated)
  }

  const deleteCard = async () => {
    await api.cards.delete(card.id)
    setActiveCard(null)
  }

  return (
    <div className="w-96 bg-gray-900 border-l border-gray-800 flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
        <h2 className="text-white font-semibold text-sm leading-snug flex-1 pr-2">{card.title}</h2>
        <button onClick={() => setActiveCard(null)} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Status + Priority */}
        <div className="flex gap-2">
          <select
            value={card.status}
            onChange={e => updateStatus(e.target.value)}
            className="flex-1 bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700"
          >
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>
          <select
            value={card.priority}
            onChange={e => updatePriority(e.target.value)}
            className="flex-1 bg-gray-800 text-white text-xs rounded px-2 py-1.5 border border-gray-700"
          >
            {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        {/* Assigned LLM */}
        {card.assigned_llm && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-1">Assigned to</div>
            <div className="text-violet-400 text-sm">🤖 {card.assigned_llm}</div>
          </div>
        )}

        {/* Description */}
        {card.description && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-1">Description</div>
            <p className="text-gray-300 text-sm whitespace-pre-wrap">{card.description}</p>
          </div>
        )}

        {/* Acceptance criteria */}
        {card.acceptance && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-1">Acceptance Criteria</div>
            <pre className="text-gray-300 text-xs whitespace-pre-wrap font-sans">{card.acceptance}</pre>
          </div>
        )}

        {/* Linked files */}
        {card.linked_files.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-1">Linked Files</div>
            {card.linked_files.map(f => (
              <div key={f} className="text-indigo-400 text-xs font-mono">{f}</div>
            ))}
          </div>
        )}

        {/* Tags */}
        {card.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {card.tags.map(t => (
              <span key={t} className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full">{t}</span>
            ))}
          </div>
        )}

        {/* Milestones */}
        {milestones.length > 0 && (
          <div>
            <div className="text-xs text-gray-500 uppercase mb-2">Milestones</div>
            <div className="space-y-1">
              {milestones.map(m => (
                <div key={m.id} className="flex items-start gap-2 text-xs">
                  <span className="text-green-400 mt-0.5">✓</span>
                  <span className="text-gray-300">{m.body}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Log stream */}
        <div>
          <div className="text-xs text-gray-500 uppercase mb-2">Live Log</div>
          <LogStream events={cardEvents} />
        </div>

        {/* Timestamps */}
        <div className="text-xs text-gray-600 space-y-0.5 border-t border-gray-800 pt-3">
          {card.created_at && <div>Created: {new Date(card.created_at).toLocaleString()}</div>}
          {card.started_at && <div>Started: {new Date(card.started_at).toLocaleString()}</div>}
          {card.completed_at && <div>Completed: {new Date(card.completed_at).toLocaleString()}</div>}
        </div>

        <button
          onClick={deleteCard}
          className="w-full text-xs text-red-500 hover:text-red-400 py-2 border border-red-900 hover:border-red-800 rounded-lg transition-colors"
        >
          Delete card
        </button>
      </div>
    </div>
  )
}
