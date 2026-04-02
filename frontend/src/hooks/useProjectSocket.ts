import { useEffect } from 'react'
import { useStore } from '../store'
import { api } from '../api/client'

export function useProjectSocket(projectId: string | null) {
  const { upsertCard, removeCard, appendEvent } = useStore()

  useEffect(() => {
    if (!projectId) return
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${location.host}/ws/projects/${projectId}`)

    ws.onmessage = async (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'card.created' || msg.type === 'card.updated') {
        const card = await api.cards.get(msg.card_id)
        upsertCard(card)
      } else if (msg.type === 'card.deleted') {
        removeCard(msg.card_id)
      } else if (msg.type === 'card.log' || msg.type === 'card.milestone') {
        appendEvent({
          id: crypto.randomUUID(),
          card_id: msg.card_id,
          type: msg.type === 'card.log' ? 'log' : 'milestone',
          body: msg.body,
          actor: msg.actor,
          meta: null,
          created_at: new Date().toISOString(),
        })
      }
    }

    return () => ws.close()
  }, [projectId, upsertCard, removeCard, appendEvent])
}
