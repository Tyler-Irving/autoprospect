import { NavLink } from 'react-router-dom'

const NAV = [
  {
    to: '/',
    label: 'Map',
    icon: (
      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
        <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
        <line x1="8" y1="2" x2="8" y2="18"/>
        <line x1="16" y1="6" x2="16" y2="22"/>
      </svg>
    ),
  },
  {
    to: '/scans',
    label: 'Scans',
    icon: (
      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
    ),
  },
  {
    to: '/leads',
    label: 'Leads',
    icon: (
      <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
    ),
  },
]

const SETTINGS_ICON = (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" viewBox="0 0 24 24">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>
)

export default function Sidebar() {
  return (
    <aside className="w-14 flex-shrink-0 flex flex-col items-center py-3 gap-1" style={{ background: 'var(--sidebar)', borderRight: '1px solid var(--sidebar-border)' }}>
      {/* Logo tile */}
      <div
        className="mb-3 flex items-center justify-center text-white font-extrabold text-xs tracking-tight"
        style={{ width: 32, height: 32, borderRadius: 8, background: '#f97316', flexShrink: 0 }}
      >
        AP
      </div>

      {/* Nav items */}
      {NAV.map(({ to, label, icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          title={label}
          className={({ isActive }) =>
            [
              'relative flex items-center justify-center rounded-lg transition-colors',
              'w-9 h-9',
              isActive
                ? 'text-white'
                : 'text-[#737373] hover:text-[#fafafa]',
            ].join(' ')
          }
          style={({ isActive }) => ({
            background: isActive ? 'var(--sidebar-accent)' : 'transparent',
          })}
        >
          {({ isActive }) => (
            <>
              {/* Active left-edge indicator */}
              {isActive && (
                <span
                  className="absolute"
                  style={{
                    left: -1,
                    top: '50%',
                    transform: 'translateY(-50%)',
                    width: 2,
                    height: 18,
                    background: '#f97316',
                    borderRadius: '0 2px 2px 0',
                  }}
                />
              )}
              {icon}
            </>
          )}
        </NavLink>
      ))}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Settings — non-navigable placeholder */}
      <button
        title="Settings"
        className="flex items-center justify-center rounded-lg w-9 h-9 transition-colors text-[#737373] hover:text-[#fafafa]"
        style={{ background: 'transparent', border: 'none', cursor: 'pointer' }}
      >
        {SETTINGS_ICON}
      </button>
    </aside>
  )
}
