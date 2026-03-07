import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'

// Avoid animating motion.aside inline — named ref prevents false lint warnings
const MotionAside = motion.aside

// Material Design "standard" easing — feels physical, not mechanical
const EASE = [0.4, 0, 0.2, 1]
const SIDEBAR_W_OPEN = 184
const SIDEBAR_W_CLOSED = 56

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

// Label transitions: opacity + translateX only (GPU-composited, zero reflow)
// Enter: slight delay so sidebar width settles first; Exit: snappy
function labelStyle(open, reduced) {
  if (reduced) return { opacity: open ? 1 : 0 }
  return {
    opacity: open ? 1 : 0,
    transform: open ? 'translateX(0)' : 'translateX(-6px)',
    transition: open
      ? 'opacity 0.15s ease-out 0.06s, transform 0.15s ease-out 0.06s'
      : 'opacity 0.09s ease-in, transform 0.09s ease-in',
  }
}

function NavItem({ to, label, icon, open, end, reduced }) {
  return (
    <NavLink
      to={to}
      end={end}
      aria-label={label}
      className={({ isActive }) =>
        [
          'relative flex items-center gap-3 rounded-lg h-9 cursor-pointer',
          'transition-colors duration-150',
          isActive ? 'text-white' : 'text-[#737373] hover:text-[#fafafa]',
        ].join(' ')
      }
      style={({ isActive }) => ({
        background: isActive ? 'var(--sidebar-accent)' : 'transparent',
        // Consistent left padding keeps icon at ~26px centre in 56px collapsed state
        paddingLeft: 20,
        paddingRight: 10,
      })}
    >
      {({ isActive }) => (
        <>
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

          <span className="shrink-0 flex items-center justify-center" style={{ width: 16 }}>
            {icon}
          </span>

          {/* Always in DOM — clipped by aside overflow:hidden when collapsed.
              Only opacity + translateX animate (no width, no reflow). */}
          <span
            aria-hidden={!open}
            className="text-xs font-medium whitespace-nowrap select-none"
            style={{
              color: isActive ? '#fafafa' : 'inherit',
              ...labelStyle(open, reduced),
            }}
          >
            {label}
          </span>
        </>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const [open, setOpen] = useState(false)
  const reduced = useReducedMotion()

  return (
    <MotionAside
      onHoverStart={() => setOpen(true)}
      onHoverEnd={() => setOpen(false)}
      initial={false}
      animate={{ width: open ? SIDEBAR_W_OPEN : SIDEBAR_W_CLOSED }}
      transition={reduced ? { duration: 0 } : { duration: 0.22, ease: EASE }}
      className="flex-shrink-0 flex flex-col py-3 gap-1 overflow-hidden"
      style={{
        background: 'var(--sidebar)',
        borderRight: '1px solid var(--sidebar-border)',
        willChange: 'width',
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 mb-3" style={{ paddingLeft: 12, paddingRight: 10 }}>
        <div
          className="shrink-0 flex items-center justify-center text-white font-extrabold text-xs tracking-tight"
          style={{ width: 32, height: 32, borderRadius: 8, background: '#f97316' }}
        >
          AP
        </div>
        <span
          aria-hidden={!open}
          className="text-xs font-semibold whitespace-nowrap select-none"
          style={{ color: 'var(--foreground)', ...labelStyle(open, reduced) }}
        >
          AutoProspect
        </span>
      </div>

      {NAV.map(({ to, label, icon }) => (
        <NavItem key={to} to={to} label={label} icon={icon} open={open} end={to === '/'} reduced={reduced} />
      ))}

      <div className="flex-1" />

      <NavItem to="/settings" label="Settings" icon={SETTINGS_ICON} open={open} reduced={reduced} />
    </MotionAside>
  )
}
