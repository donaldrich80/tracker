import { create } from 'zustand'
import { api } from '../api/client'
import type { Project, Card, CardEvent } from '../api/client'

interface TrackerStore {
  projects: Project[]
  activeProjectId: string | null
  cards: Record<string, Card[]>         // projectId -> cards
  activeCardId: string | null
  events: Record<string, CardEvent[]>   // cardId -> events

  loadProjects: () => Promise<void>
  setActiveProject: (id: string) => void
  loadCards: (projectId: string) => Promise<void>
  setActiveCard: (id: string | null) => void
  loadEvents: (cardId: string) => Promise<void>
  upsertCard: (card: Card) => void
  removeCard: (cardId: string) => void
  appendEvent: (event: CardEvent) => void
  scan: () => Promise<void>
}

export const useStore = create<TrackerStore>((set, get) => ({
  projects: [],
  activeProjectId: null,
  cards: {},
  activeCardId: null,
  events: {},

  loadProjects: async () => {
    const projects = await api.projects.list()
    set({ projects })
    if (!get().activeProjectId && projects.length > 0) {
      get().setActiveProject(projects[0].id)
    }
  },

  setActiveProject: (id) => {
    set({ activeProjectId: id, activeCardId: null })
    get().loadCards(id)
  },

  loadCards: async (projectId) => {
    const cards = await api.cards.list(projectId)
    set(s => ({ cards: { ...s.cards, [projectId]: cards } }))
  },

  setActiveCard: (id) => {
    set({ activeCardId: id })
    if (id) get().loadEvents(id)
  },

  loadEvents: async (cardId) => {
    const events = await api.events.list(cardId)
    set(s => ({ events: { ...s.events, [cardId]: events } }))
  },

  upsertCard: (card) => {
    set(s => {
      const existing = s.cards[card.project_id] || []
      const idx = existing.findIndex(c => c.id === card.id)
      const updated = idx >= 0
        ? existing.map(c => c.id === card.id ? card : c)
        : [...existing, card]
      return { cards: { ...s.cards, [card.project_id]: updated } }
    })
  },

  removeCard: (cardId) => {
    set(s => {
      const newCards = { ...s.cards }
      for (const pid in newCards) {
        newCards[pid] = newCards[pid].filter(c => c.id !== cardId)
      }
      return { cards: newCards }
    })
  },

  appendEvent: (event) => {
    set(s => ({
      events: {
        ...s.events,
        [event.card_id]: [...(s.events[event.card_id] || []), event],
      }
    }))
  },

  scan: async () => {
    await api.projects.scan()
    await get().loadProjects()
  },
}))
