import { useStore } from '../store'

interface Props {
  view: 'kanban' | 'list'
  onViewChange: (v: 'kanban' | 'list') => void
}

export function BoardHeader({ view, onViewChange }: Props) {
  const { projects, activeProjectId, scan } = useStore()
  const project = projects.find(p => p.id === activeProjectId)
  if (!project) return null

  return (
    <div className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
      <div className="flex items-center gap-4">
        <h1 className="text-white font-semibold text-lg">{project.name}</h1>
        {project.git_branch && (
          <span className="text-green-400 text-sm font-mono">{project.git_branch}</span>
        )}
        {project.git_dirty && (
          <span className="text-yellow-400 text-xs">● uncommitted changes</span>
        )}
        {project.git_last_commit && (
          <span className="text-gray-500 text-xs truncate max-w-xs">{project.git_last_commit}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onViewChange('kanban')}
          className={`px-2 py-1 text-xs rounded ${view === 'kanban' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
        >
          ⊞ Kanban
        </button>
        <button
          onClick={() => onViewChange('list')}
          className={`px-2 py-1 text-xs rounded ${view === 'list' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white'}`}
        >
          ☰ List
        </button>
        <button
          onClick={scan}
          className="px-3 py-1 text-xs bg-gray-700 hover:bg-gray-600 text-white rounded ml-2"
        >
          Rescan
        </button>
      </div>
    </div>
  )
}
