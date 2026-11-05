// =====================================================================
// PhotoUploader.jsx  —  lets the user choose their own photo.
// =====================================================================
// Shows a big clickable area. After a photo is chosen it shows a preview.
//
// Props:
//   previewUrl   -> address of the preview image (or null if none chosen)
//   onPhotoSelected(file) -> called with the chosen File object
//   disabled     -> true while the AI is working (no changes allowed)
//
// The photo is NOT uploaded here. It stays in the browser until the user
// clicks "Generate Try-On" (see TryOnPage.jsx).

import { useRef } from 'react'

function PhotoUploader({ previewUrl, onPhotoSelected, disabled = false }) {
  // useRef gives us a handle to the hidden <input type="file">,
  // so our nice-looking button can "click" it.
  const fileInputRef = useRef(null)

  function openFilePicker() {
    fileInputRef.current.click()
  }

  function handleFileChange(event) {
    const chosenFile = event.target.files[0]
    if (chosenFile) {
      onPhotoSelected(chosenFile)
    }
    // Clear the input so choosing the SAME file again still triggers a change.
    event.target.value = ''
  }

  return (
    <div>
      {/* The real file input is hidden; "accept" filters the file picker. */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={handleFileChange}
        className="hidden"
      />

      <button
        type="button"
        onClick={openFilePicker}
        disabled={disabled}
        className="group relative flex aspect-[4/5] w-full items-center justify-center overflow-hidden rounded-2xl border-2 border-dashed border-stone-300 bg-white transition hover:border-brand disabled:cursor-not-allowed disabled:opacity-60"
      >
        {previewUrl ? (
          <>
            <img src={previewUrl} alt="Your uploaded photo" className="h-full w-full object-cover" />
            <span className="absolute bottom-3 rounded-full bg-black/60 px-3 py-1 text-xs text-white">
              Click to change photo
            </span>
          </>
        ) : (
          <div className="p-6 text-center text-muted">
            <div className="mb-2 text-4xl">📷</div>
            <p className="font-medium text-ink">Upload your photo</p>
            <p className="mt-1 text-xs">JPEG, PNG or WebP · max 10 MB</p>
          </div>
        )}
      </button>

      {/* Image quality guidance, as recommended in the project specification. */}
      {/* TODO: Adjust these tips after testing which photos give the best results. */}
      <ul className="mt-3 space-y-1 text-xs text-muted">
        <li>✓ Stand facing the camera, full upper body visible</li>
        <li>✓ Good lighting, plain background, one person only</li>
        <li>🔒 Your photo is only used to create the preview and is deleted from our server right after.</li>
      </ul>
    </div>
  )
}

export default PhotoUploader
