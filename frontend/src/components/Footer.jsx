// =====================================================================
// Footer.jsx  —  the strip at the bottom of every page.
// =====================================================================

// Gets the current year automatically, e.g. 2026.
// It is calculated once when the app loads (outside the component),
// so it doesn't change between redraws.
const CURRENT_YEAR = new Date().getFullYear()

function Footer() {
  const currentYear = CURRENT_YEAR

  return (
    <footer className="border-t border-stone-200 bg-white">
      <div className="mx-auto max-w-6xl px-4 py-6 text-center text-sm text-muted">
        {/* TODO: Add your university / company / project information here. */}
        <p>© {currentYear} AI Virtual Try-On · Phase 1 MVP</p>
        <p className="mt-1 text-xs">
          Try-on images are AI-generated previews of appearance, not a guarantee of fit.
        </p>
      </div>
    </footer>
  )
}

export default Footer
