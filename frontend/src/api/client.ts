const BASE = '/api/v1'

export interface Project {
  id: string; name: string; stack: string[]
  git_branch: string | null; git_dirty: boolean; git_last_commit: string | null
  description: string | null; active: boolean
}

export interface Card {
  id: string; project_id: string; title: string; description: string | null
  status: 'todo' | 'in_progress' | 'review' | 'done' | 'blocked'
  priority: 'low' | 'medium' | 'high'; assigned_llm: string | null
  tags: string[]; linked_files: string[]; acceptance: string | null
  blocks: string[]; blocked_by: string[]
  created_at: string | null; started_at: string | null; completed_at: string | null
}

export interface CardEvent {
  id: string; card_id: string; type: string; body: string | null
  actor: string | null; meta: Record<string, unknown> | null; created_at: string | null
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${method} ${path} → ${res.status}`)
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  projects: {
    list: () => req<Project[]>('GET', '/projects'),
    scan: () => req<{ scanned: number }>('POST', '/projects/scan'),
  },
  cards: {
    list: (projectId: string) => req<Card[]>('GET', `/projects/${projectId}/cards`),
    create: (projectId: string, data: Partial<Card>) => req<Card>('POST', `/projects/${projectId}/cards`, data),
    get: (id: string) => req<Card>('GET', `/cards/${id}`),
    update: (id: string, data: Partial<Card>) => req<Card>('PATCH', `/cards/${id}`, data),
    delete: (id: string) => req<void>('DELETE', `/cards/${id}`),
  },
  events: {
    list: (cardId: string) => req<CardEvent[]>('GET', `/cards/${cardId}/events`),
    log: (cardId: string, body: string) => req<CardEvent>('POST', `/cards/${cardId}/log`, { body, actor: 'user' }),
    milestone: (cardId: string, body: string) => req<CardEvent>('POST', `/cards/${cardId}/milestone`, { body, actor: 'user' }),
  },
  search: (q: string) => req<Card[]>('GET', `/search?q=${encodeURIComponent(q)}`),
}
