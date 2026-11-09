// =====================================================================
// ViewAnglePanel.jsx  —  "See it from another angle" (beta).
// =====================================================================
// The user picks where the camera should move (left/right, above/below)
// and the AI redraws the SAME person and outfit from that viewpoint.
//
// Props:
//   sourceUrl -> the image to redraw (the try-on result, or its rotated copy)
//   productId -> used for the download file name
//
// The parent gives this component key={sourceUrl}, so when a NEW result
// appears, React creates a fresh panel and all old state is cleared.

import { useState } from 'react'
import { createNewAngle, downloadImage } from '../services/api.js'
import LoadingSpinner from './LoadingSpinner.jsx'

// Camera height choices -> value the backend expects.
const CAMERA_HEIGHTS = [
  { label: 'Eye level', value: 0 },
  { label: 'From above', value: -1 },
  { label: 'From below', value: 1 },
]

// Text shown next to the slider, e.g. "45° to the left".
function describeCameraPosition(sliderValue) {
  if (sliderValue === 0) {
    return 'Straight on (no turn)'
  }
  const side = sliderValue < 0 ? 'left' : 'right'
  return `${Math.abs(sliderValue)}° to the ${side}`
}

function ViewAnglePanel({ sourceUrl, productId }) {
  // Slider: -90 (camera far left) ... 0 ... 90 (camera far right).
  const [cameraPosition, setCameraPosition] = useState(-45)
  const [cameraHeight, setCameraHeight] = useState(0)

  const [isGenerating, setIsGenerating] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [newImageUrl, setNewImageUrl] = useState(null)

  const nothingChosen = cameraPosition === 0 && cameraHeight === 0

  async function handleGenerate() {
    setErrorMessage('')
    setIsGenerating(true)
    try {
      // The AI uses "positive = left", our slider uses "left = negative",
      // so we flip the sign.
      const result = await createNewAngle(sourceUrl, -cameraPosition, cameraHeight)
      setNewImageUrl(result.image_url)
    } catch (error) {
      setErrorMessage(error.message)
    } finally {
      setIsGenerating(false)
    }
  }

  function handleDownload() {
    const fileName = `virtual-tryon-${productId}-angle.png`
    downloadImage(newImageUrl, fileName).catch((error) => setErrorMessage(error.message))
  }

  return (
    <div className="mt-8 border-t border-stone-200 pt-6">
      <h3 className="text-center font-display text-xl font-semibold">See it from another angle (beta)</h3>

      {/* ---------- Controls ---------- */}
      <div className="mx-auto mt-5 max-w-md space-y-4">
        <label className="block">
          <span className="flex justify-between text-sm">
            <span className="font-medium">Camera direction</span>
            <span className="text-muted">{describeCameraPosition(cameraPosition)}</span>
          </span>
          <input
            type="range"
            min="-90"
            max="90"
            step="15"
            value={cameraPosition}
            onChange={(event) => setCameraPosition(Number(event.target.value))}
            disabled={isGenerating}
            className="mt-2 w-full accent-brand"
          />
          <span className="flex justify-between text-xs text-muted">
            <span>← Left side</span>
            <span>Front</span>
            <span>Right side →</span>
          </span>
        </label>

        <div>
          <span className="text-sm font-medium">Camera height</span>
          <div className="mt-2 flex gap-2">
            {CAMERA_HEIGHTS.map((height) => (
              <button
                key={height.value}
                type="button"
                onClick={() => setCameraHeight(height.value)}
                disabled={isGenerating}
                className={`flex-1 rounded-full border px-3 py-1.5 text-sm transition ${
                  cameraHeight === height.value ? 'border-ink bg-ink text-white' : 'border-stone-300 hover:border-ink'
                }`}
              >
                {height.label}
              </button>
            ))}
          </div>
        </div>

        <div className="text-center">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={isGenerating || nothingChosen}
            className="rounded-full bg-ink px-8 py-3 font-medium text-white transition hover:opacity-90 disabled:opacity-40"
          >
            {newImageUrl ? 'Try this angle' : 'Generate new angle'}
          </button>
          {nothingChosen && <p className="mt-2 text-xs text-muted">Move the slider or pick a camera height first.</p>}
        </div>
      </div>

      {/* ---------- Waiting ---------- */}
      {isGenerating && (
        <LoadingSpinner message="Redrawing from the new angle... this usually takes 20–60 seconds." />
      )}

      {/* ---------- Error ---------- */}
      {errorMessage && !isGenerating && (
        <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-center text-sm text-red-700">{errorMessage}</p>
      )}

      {/* ---------- Result: original vs new angle ---------- */}
      {newImageUrl && !isGenerating && (
        <div className="mt-6">
          <div className="grid grid-cols-2 gap-3 sm:gap-6">
            <figure>
              <img src={sourceUrl} alt="Try-on result, original angle" className="aspect-[4/5] w-full rounded-xl bg-stone-100 object-contain" />
              <figcaption className="mt-2 text-center text-sm text-muted">Original</figcaption>
            </figure>
            <figure>
              <img src={newImageUrl} alt="Try-on result from a new angle" className="aspect-[4/5] w-full rounded-xl bg-stone-100 object-contain" />
              <figcaption className="mt-2 text-center text-sm font-medium text-brand">New angle</figcaption>
            </figure>
          </div>
          <div className="mt-4 text-center">
            <button
              type="button"
              onClick={handleDownload}
              className="rounded-full border border-stone-300 px-6 py-2 text-sm transition hover:border-ink"
            >
              ⬇ Download new angle
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default ViewAnglePanel
