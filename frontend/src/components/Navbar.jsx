import { Link, NavLink } from 'react-router-dom'

// TODO: Add more menu items here (e.g. { label: 'About', path: '/about' }).
const MENU_ITEMS = [
  { label: 'Home', path: '/' },
  { label: 'Catalog', path: '/catalog' },
  { label: 'Try-On', path: '/try-on' },
]

if (import.meta.env.VITE_SHOW_MANAGE !== 'false') {
  MENU_ITEMS.push({ label: 'Manage', path: '/manage' })
}

function Navbar() {
  function getLinkClasses({ isActive }) {
    const baseClasses = 'rounded-full px-2 py-1.5 text-sm font-medium transition-colors sm:px-3'
    if (isActive) {
      return `${baseClasses} bg-brand-light text-brand-dark`
    }
    return `${baseClasses} text-muted hover:text-ink`
  }

  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        {/* TODO: Replace the text logo with your own logo image if you like. */}
        <Link to="/" className="shrink-0 font-display text-base font-semibold sm:text-xl">
          AI Virtual <span className="text-brand">Try-On</span>
        </Link>

        <div className="flex items-center gap-0.5 sm:gap-1">
          {MENU_ITEMS.map((item) => (
            <NavLink key={item.path} to={item.path} end className={getLinkClasses}>
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </header>
  )
}

export default Navbar
