import { useEffect, useState } from 'react'
import { useStore } from './store'
import { ProjectTabs } from './components/ProjectTabs'
import { BoardHeader } from './components/BoardHeader'
import { KanbanBoard } from './components/KanbanBoard'
import { ListView } from './components/ListView'
import { CardDetail } from './components/CardDetail'
import { useProjectSocket } from './hooks/useProjectSocket'

export default function App() {
  const { loadProjects, activeProjectId, activeCardId } = useStore()
  const [view, setView] = useState<'kanban' | 'list'>('kanban')
  useProjectSocket(activeProjectId)

  useEffect(() => { loadProjects() }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <nav className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
        <span className="font-bold text-indigo-400 text-lg">⬡ Tracker</span>
      </nav>
      <ProjectTabs />
      {activeProjectId && (
        <>
          <BoardHeader view={view} onViewChange={setView} />
          <div className="flex flex-1 overflow-hidden">
            <div className="flex-1 overflow-auto">
              {view === 'kanban' ? <KanbanBoard /> : <ListView />}
            </div>
            {activeCardId && <CardDetail />}
          </div>
        </>
      )}
      {!activeProjectId && (
        <div className="flex-1 flex items-center justify-center text-gray-600">
          No projects found. Make sure your projects folder is mounted.
        </div>
      )}
    </div>
  )
}
