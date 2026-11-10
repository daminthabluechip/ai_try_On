import { useRef } from 'react'

function PhotoUploader({ previewUrl, onPhotoSelected, disabled = false }) {
  const fileInputRef = useRef(null)

  function openFilePicker() {
    fileInputRef.current.click()
  }

  function handleFileChange(event) {
    const chosenFile = event.target.files[0]
    if (chosenFile) {
      onPhotoSelected(chosenFile)
    }
    event.target.value = ''
  }

  return (
    <div>
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
