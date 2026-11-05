// =====================================================================
// Navbar.jsx  —  the menu bar at the top of every page.
// =====================================================================
// NavLink is a special link from React Router: it changes the page
// WITHOUT reloading the browser, and tells us if it is the current page
// (isActive) so we can highlight it.

import { Link, NavLink } from 'react-router-dom'

// TODO: Add more menu items here (e.g. { label: 'About', path: '/about' }).
//       Remember to also create the page and add a <Route> in App.jsx.
const MENU_ITEMS = [
  { label: 'Home', path: '/' },
  { label: 'Catalog', path: '/catalog' },
  { label: 'Try-On', path: '/try-on' },
  // TODO (before going online): remove this item, and set
  //   ALLOW_PRODUCT_MANAGEMENT=false in backend/.env
  { label: 'Manage', path: '/manage' },
]

function Navbar() {
  // Returns the CSS classes for a menu link; the current page is highlighted.
  function getLinkClasses({ isActive }) {
    // Smaller padding on phones (px-2), more on bigger screens (sm:px-3).
    const baseClasses = 'rounded-full px-2 py-1.5 text-sm font-medium transition-colors sm:px-3'
    if (isActive) {
      return `${baseClasses} bg-brand-light text-brand-dark`
    }
    return `${baseClasses} text-muted hover:text-ink`
  }

  return (
    <header className="sticky top-0 z-10 border-b border-stone-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        {/* Logo / project name — clicking it goes to the home page */}
        {/* TODO: Replace the text logo with your own logo image if you like. */}
        <Link to="/" className="shrink-0 font-display text-base font-semibold sm:text-xl">
          AI Virtual <span className="text-brand">Try-On</span>
        </Link>

        <div className="flex items-center gap-0.5 sm:gap-1">
          {MENU_ITEMS.map((item) => (
            // "end" makes "/" active only on the home page, not on every page.
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
