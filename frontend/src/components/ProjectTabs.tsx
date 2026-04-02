import { useStore } from '../store'

export function ProjectTabs() {
  const { projects, activeProjectId, setActiveProject } = useStore()

  return (
    <div className="flex gap-1 overflow-x-auto px-4 py-2 bg-gray-900 border-b border-gray-800">
      {projects.filter(p => p.active).map(p => (
        <button
          key={p.id}
          onClick={() => setActiveProject(p.id)}
          className={`px-3 py-1 rounded-full text-sm whitespace-nowrap transition-colors ${
            activeProjectId === p.id
              ? 'bg-indigo-600 text-white'
              : 'bg-gray-800 text-gray-400 hover:text-white'
          }`}
        >
          {p.name}
        </button>
      ))}
    </div>
  )
}
