import type { Card } from '../api/client'
import { useStore } from '../store'

const PRIORITY_COLORS = { low: 'border-gray-600', medium: 'border-yellow-500', high: 'border-red-500' }
const LLM_COLORS: Record<string, string> = { claude: 'text-violet-400', kimi: 'text-blue-400' }

interface Props { card: Card; compact?: boolean }

export function CardItem({ card, compact }: Props) {
  const { setActiveCard, activeCardId } = useStore()
  const isActive = activeCardId === card.id

  return (
    <div
      onClick={() => setActiveCard(isActive ? null : card.id)}
      className={`cursor-pointer rounded-lg p-3 mb-2 border-l-4 transition-colors
        ${PRIORITY_COLORS[card.priority]}
        ${isActive ? 'bg-indigo-900/40 ring-1 ring-indigo-500' : 'bg-gray-800 hover:bg-gray-750'}`}
    >
      <div className="text-sm font-medium text-white leading-snug">{card.title}</div>
      <div className="flex items-center gap-2 mt-1.5 flex-wrap">
        {card.tags.map(t => (
          <span key={t} className="text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">{t}</span>
        ))}
        {card.assigned_llm && (
          <span className={`text-xs font-medium ${LLM_COLORS[card.assigned_llm] || 'text-gray-400'}`}>
            🤖 {card.assigned_llm}
          </span>
        )}
        {card.status === 'in_progress' && card.assigned_llm && (
          <span className="text-xs text-green-400">● live</span>
        )}
      </div>
      {!compact && card.blocked_by.length > 0 && (
        <div className="mt-1 text-xs text-red-400">⛔ blocked</div>
      )}
    </div>
  )
}
