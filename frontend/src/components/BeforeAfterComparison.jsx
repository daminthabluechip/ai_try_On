// =====================================================================
// BeforeAfterComparison.jsx  —  compare the original photo with the
// generated try-on image.
// =====================================================================
// Two view modes the user can switch between:
//   "Side by side" -> both images next to each other (default)
//   "Slider"       -> images on top of each other; drag the slider to
//                     reveal more of "before" or "after"
//
// Props:
//   beforeUrl -> the user's original photo
//   afterUrl  -> the generated try-on image
//
// Note: the AI crops the photo around the person (4:5 shape), so in the
// slider view the two images may not line up perfectly.
// The "after" image uses object-contain (whole image visible, no cropping),
// so it still fits nicely after the user rotates it sideways.

import { useState } from 'react'

const VIEW_SIDE_BY_SIDE = 'side-by-side'
const VIEW_SLIDER = 'slider'

function BeforeAfterComparison({ beforeUrl, afterUrl }) {
  const [viewMode, setViewMode] = useState(VIEW_SIDE_BY_SIDE)

  // How much of the "before" image is visible in slider mode (0–100 %).
  const [sliderPercent, setSliderPercent] = useState(50)

  // Classes for the two view-mode buttons (the active one is dark).
  function getToggleClasses(mode) {
    const baseClasses = 'rounded-full px-4 py-1.5 text-sm transition-colors'
    if (viewMode === mode) {
      return `${baseClasses} bg-ink text-white`
    }
    return `${baseClasses} text-muted hover:text-ink`
  }

  return (
    <div>
      {/* ---------- View mode switch ---------- */}
      <div className="mb-4 flex justify-center">
        <div className="inline-flex rounded-full border border-stone-200 bg-stone-50 p-1">
          <button type="button" onClick={() => setViewMode(VIEW_SIDE_BY_SIDE)} className={getToggleClasses(VIEW_SIDE_BY_SIDE)}>
            Side by side
          </button>
          <button type="button" onClick={() => setViewMode(VIEW_SLIDER)} className={getToggleClasses(VIEW_SLIDER)}>
            Slider
          </button>
        </div>
      </div>

      {/* ---------- Side-by-side view ---------- */}
      {viewMode === VIEW_SIDE_BY_SIDE && (
        <div className="grid grid-cols-2 gap-3 sm:gap-6">
          <figure>
            <img src={beforeUrl} alt="Your original photo" className="aspect-[4/5] w-full rounded-xl bg-stone-100 object-cover" />
            <figcaption className="mt-2 text-center text-sm text-muted">Before</figcaption>
          </figure>
          <figure>
            <img src={afterUrl} alt="AI try-on result" className="aspect-[4/5] w-full rounded-xl bg-stone-100 object-contain" />
            <figcaption className="mt-2 text-center text-sm font-medium text-brand">After</figcaption>
          </figure>
        </div>
      )}

      {/* ---------- Slider view ---------- */}
      {viewMode === VIEW_SLIDER && (
        <div className="mx-auto max-w-md">
          {/* "relative" lets us stack the images on top of each other */}
          <div className="relative aspect-[4/5] overflow-hidden rounded-xl bg-stone-100 select-none">
            {/* Bottom layer: the AFTER image (always fully visible) */}
            <img src={afterUrl} alt="AI try-on result" className="absolute inset-0 h-full w-full object-contain" />

            {/* Top layer: the BEFORE image, cut off on the right side.
                clip-path "inset(0 X% 0 0)" hides X% from the right edge. */}
            <img
              src={beforeUrl}
              alt="Your original photo"
              className="absolute inset-0 h-full w-full object-cover"
              style={{ clipPath: `inset(0 ${100 - sliderPercent}% 0 0)` }}
            />

            {/* The white dividing line */}
            <div
              className="pointer-events-none absolute inset-y-0 w-0.5 bg-white shadow"
              style={{ left: `${sliderPercent}%` }}
            />

            {/* Labels */}
            <span className="absolute top-3 left-3 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white">Before</span>
            <span className="absolute top-3 right-3 rounded-full bg-brand px-2 py-0.5 text-xs text-white">After</span>

            {/* An invisible range input covering the whole image: dragging
                anywhere (mouse or finger) moves the slider. It also works
                with the keyboard arrow keys. */}
            <input
              type="range"
              min="0"
              max="100"
              value={sliderPercent}
              onChange={(event) => setSliderPercent(Number(event.target.value))}
              aria-label="Drag to compare before and after"
              className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
            />
          </div>
          <p className="mt-2 text-center text-xs text-muted">Drag across the image to compare.</p>
        </div>
      )}
    </div>
  )
}

export default BeforeAfterComparison
