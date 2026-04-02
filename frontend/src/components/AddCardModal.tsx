import { useState } from 'react'
import { useStore } from '../store'
import { api } from '../api/client'

interface Props { projectId: string; onClose: () => void }

export function AddCardModal({ projectId, onClose }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<'low' | 'medium' | 'high'>('medium')
  const { upsertCard } = useStore()

  const submit = async () => {
    if (!title.trim()) return
    const card = await api.cards.create(projectId, { title, description, priority })
    upsertCard(card)
    onClose()
  }

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md" onClick={e => e.stopPropagation()}>
        <h2 className="text-white font-semibold text-lg mb-4">Add Card</h2>
        <input
          autoFocus
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Card title"
          className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 mb-3 text-sm border border-gray-700 focus:outline-none focus:border-indigo-500"
        />
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Description (optional)"
          rows={3}
          className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 mb-3 text-sm border border-gray-700 focus:outline-none focus:border-indigo-500 resize-none"
        />
        <select
          value={priority}
          onChange={e => setPriority(e.target.value as 'low' | 'medium' | 'high')}
          className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 mb-4 text-sm border border-gray-700 focus:outline-none"
        >
          <option value="low">Low priority</option>
          <option value="medium">Medium priority</option>
          <option value="high">High priority</option>
        </select>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-gray-400 hover:text-white">Cancel</button>
          <button onClick={submit} className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg">Add Card</button>
        </div>
      </div>
    </div>
  )
}
