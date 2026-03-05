import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Map', icon: '🗺️' },
  { to: '/leads', label: 'Leads', icon: '📋' },
]

export default function Sidebar() {
  return (
    <aside className="w-14 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col items-center py-4 gap-2">
      <div className="mb-4 text-blue-400 font-bold text-xs">AP</div>
      {NAV.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          title={label}
          className={({ isActive }) =>
            `flex flex-col items-center gap-1 px-2 py-2 rounded-lg text-xs transition-colors w-10 ${
              isActive ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`
          }
        >
          <span className="text-base leading-none">{icon}</span>
          <span className="text-[10px]">{label}</span>
        </NavLink>
      ))}
    </aside>
  )
}
