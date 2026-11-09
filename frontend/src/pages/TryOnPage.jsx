// =====================================================================
// TryOnPage.jsx  —  the virtual try-on page (address: "/try-on").
// =====================================================================
// The user:
//   1. uploads a photo           (PhotoUploader)
//   2. selects a clothing item   (ProductCard grid)
//   3. clicks "Generate Try-On"  -> createTryOn() in services/api.js
//   4. sees the generated image  (result section)
//   5. can reset and try another item
//
// If the address is /try-on?product=black-tshirt (coming from the
// catalog), that product is selected automatically.

import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { createTryOn, downloadImage, getProducts } from '../services/api.js'
import BeforeAfterComparison from '../components/BeforeAfterComparison.jsx'
import { rotateImage } from '../utils/rotateImage.js'
import PhotoUploader from '../components/PhotoUploader.jsx'
import ProductCard from '../components/ProductCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

// Same rules as the backend (backend/config.py). Checking here too gives
// the user instant feedback without waiting for an upload.
const ALLOWED_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_PHOTO_SIZE_MB = 10

function TryOnPage() {
  // Read "?product=..." from the address bar.
  const [searchParams] = useSearchParams()
  const productFromAddress = searchParams.get('product')

  // ---------------- State (data that changes on this page) ----------------
  const [products, setProducts] = useState([])
  const [isLoadingProducts, setIsLoadingProducts] = useState(true)

  const [photoFile, setPhotoFile] = useState(null)           // the chosen File
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState(null) // temporary address to show it

  const [selectedProductId, setSelectedProductId] = useState(productFromAddress)

  const [isGenerating, setIsGenerating] = useState(false)    // true while the AI works
  const [tryOnResult, setTryOnResult] = useState(null)       // backend answer
  const [errorMessage, setErrorMessage] = useState('')
  const [isDownloading, setIsDownloading] = useState(false)
  const [isRotating, setIsRotating] = useState(false)

  // A handle to the result section, so we can scroll to it.
  const resultSectionRef = useRef(null)

  // ---------------- Load products once when the page opens ----------------
  useEffect(() => {
    async function loadProducts() {
      try {
        const loadedProducts = await getProducts()
        setProducts(loadedProducts)
      } catch (error) {
        setErrorMessage(error.message)
      } finally {
        setIsLoadingProducts(false)
      }
    }
    loadProducts()
  }, [])

  // ---------------- Free the preview's memory when it changes ----------------
  // URL.createObjectURL() (used below) reserves browser memory for the
  // preview. This "cleanup" releases it when the photo changes or the
  // user leaves the page.
  useEffect(() => {
    return () => {
      if (photoPreviewUrl) {
        URL.revokeObjectURL(photoPreviewUrl)
      }
    }
  }, [photoPreviewUrl])

  // ---------------- Event handlers ----------------

  // Called by PhotoUploader when the user picks a file.
  function handlePhotoSelected(file) {
    setErrorMessage('')

    if (!ALLOWED_PHOTO_TYPES.includes(file.type)) {
      setErrorMessage('Please choose a JPEG, PNG or WebP image.')
      return
    }
    const fileSizeMb = file.size / (1024 * 1024)
    if (fileSizeMb > MAX_PHOTO_SIZE_MB) {
      setErrorMessage(`The photo is too large. The maximum size is ${MAX_PHOTO_SIZE_MB} MB.`)
      return
    }

    setPhotoFile(file)
    // Create a temporary local address so the <img> can show the photo
    // BEFORE it is uploaded anywhere.
    setPhotoPreviewUrl(URL.createObjectURL(file))
    setTryOnResult(null) // a new photo means the old result no longer applies
  }

  function handleProductSelected(product) {
    setSelectedProductId(product.id)
    setTryOnResult(null)
    setErrorMessage('')
  }

  // Called when "Generate Try-On" is clicked: send everything to the backend.
  async function handleGenerate() {
    setErrorMessage('')
    setTryOnResult(null)
    setIsGenerating(true)

    // Scroll down so the user sees the loading spinner.
    resultSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })

    try {
      const result = await createTryOn(photoFile, selectedProductId)
      setTryOnResult(result)
    } catch (error) {
      setErrorMessage(error.message)
    } finally {
      // "finally" runs after success OR error: always stop the spinner.
      setIsGenerating(false)
    }
  }

  // Rotate the result image. direction: 90 = right (clockwise), -90 = left.
  // The rotation is stored INSIDE tryOnResult, so a new result (or Reset)
  // automatically starts un-rotated again.
  async function handleRotate(direction) {
    const currentRotation = tryOnResult.rotation || 0
    // "+ 360" and "% 360" keep the value between 0 and 270.
    const newRotation = (currentRotation + direction + 360) % 360

    setIsRotating(true)
    try {
      let rotatedUrl = null
      if (newRotation !== 0) {
        rotatedUrl = await rotateImage(tryOnResult.result_url, newRotation)
      }
      // Free the memory of the previous rotated copy.
      if (tryOnResult.rotated_url) {
        URL.revokeObjectURL(tryOnResult.rotated_url)
      }
      setTryOnResult({ ...tryOnResult, rotation: newRotation, rotated_url: rotatedUrl })
    } catch (error) {
      setErrorMessage(error.message)
    } finally {
      setIsRotating(false)
    }
  }

  // Save the generated image (rotated, if the user rotated it).
  async function handleDownload() {
    // Keep the same file type as the result, e.g. ".png" or ".jpg".
    const resultUrl = tryOnResult.result_url
    const extension = resultUrl.substring(resultUrl.lastIndexOf('.'))
    const fileName = `virtual-tryon-${tryOnResult.product_id}${extension}`

    setIsDownloading(true)
    try {
      await downloadImage(tryOnResult.rotated_url || resultUrl, fileName)
    } catch (error) {
      setErrorMessage(error.message)
    } finally {
      setIsDownloading(false)
    }
  }

  // Keep the photo, but clear the garment and result, so the user can
  // quickly try a different item on the same photo.
  function handleTryAnotherItem() {
    setSelectedProductId(null)
    setTryOnResult(null)
    setErrorMessage('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Start over: clear the photo, selection, result and errors.
  function handleReset() {
    setPhotoFile(null)
    setPhotoPreviewUrl(null)
    setSelectedProductId(null)
    setTryOnResult(null)
    setErrorMessage('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // ---------------- Values calculated from the state ----------------
  const selectedProduct = products.find((product) => product.id === selectedProductId)
  const canGenerate = photoFile !== null && selectedProduct !== undefined && !isGenerating

  // A short hint telling the user what is still missing.
  let generateHint = 'Ready! Click Generate to see the result.'
  if (!photoFile && !selectedProduct) {
    generateHint = 'Upload a photo and select a garment to continue.'
  } else if (!photoFile) {
    generateHint = 'Upload a photo of yourself to continue.'
  } else if (!selectedProduct) {
    generateHint = 'Select a garment to continue.'
  }

  // ---------------- What the page shows ----------------
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">Virtual Try-On</h1>
      <p className="mt-2 text-muted">Upload your photo, pick a garment and let the AI do the rest.</p>

      {/* ===== Steps 1 + 2: photo (left) and garments (right) ===== */}
      <div className="mt-8 grid gap-8 lg:grid-cols-3">
        {/* Step 1 */}
        <section>
          <h2 className="mb-3 font-medium">
            <span className="text-brand">1.</span> Your photo
          </h2>
          <PhotoUploader
            previewUrl={photoPreviewUrl}
            onPhotoSelected={handlePhotoSelected}
            disabled={isGenerating}
          />
        </section>

        {/* Step 2 */}
        <section className="lg:col-span-2">
          <h2 className="mb-3 font-medium">
            <span className="text-brand">2.</span> Choose a garment
          </h2>

          {isLoadingProducts ? (
            <LoadingSpinner message="Loading products..." />
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  buttonLabel="Select"
                  onButtonClick={handleProductSelected}
                  isSelected={product.id === selectedProductId}
                />
              ))}
            </div>
          )}
        </section>
      </div>

      {/* ===== Step 3: Generate button ===== */}
      <section className="mt-10 flex flex-col items-center gap-3 rounded-2xl border border-stone-200 bg-white p-6 text-center">
        <h2 className="font-medium">
          <span className="text-brand">3.</span> Generate
        </h2>
        <p className="text-sm text-muted">{generateHint}</p>
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!canGenerate}
            className="rounded-full bg-brand px-8 py-3 font-medium text-white transition hover:bg-brand-dark disabled:cursor-not-allowed disabled:bg-stone-300"
          >
            {isGenerating ? 'Generating...' : 'Generate Try-On'}
          </button>
          <button
            type="button"
            onClick={handleReset}
            disabled={isGenerating}
            className="rounded-full border border-stone-300 px-8 py-3 font-medium transition hover:border-ink disabled:opacity-50"
          >
            Reset
          </button>
        </div>
      </section>

      {/* ===== Result ===== */}
      {/* scroll-mt-20 leaves space for the sticky navbar when scrolling here */}
      <section ref={resultSectionRef} className="mt-10 scroll-mt-20">
        <div className="mb-4">
          <ErrorMessage message={errorMessage} onDismiss={() => setErrorMessage('')} />
        </div>

        {isGenerating && (
          <LoadingSpinner message="The AI is creating your try-on... this usually takes 10–30 seconds." />
        )}

        {tryOnResult && (
          <div className="rounded-2xl border border-stone-200 bg-white p-6">
            <h2 className="font-display text-2xl font-semibold">
              Your result: {tryOnResult.product_name}
            </h2>

            {/* In mock mode, Genlook returns the photo unchanged (free testing). */}
            {tryOnResult.mock_mode && (
              <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
                Mock mode is ON: the photo is returned unchanged and no AI credits are used.
                Set TRYON_MOCK_MODE=false in backend/.env for real AI results.
              </p>
            )}

            {/* Before (the user's photo) vs After (the AI result) */}
            <div className="mt-6">
              <BeforeAfterComparison
                beforeUrl={photoPreviewUrl}
                afterUrl={tryOnResult.rotated_url || tryOnResult.result_url}
              />
            </div>

            {/* Rotate the result (also changes the downloaded image) */}
            <div className="mt-4 flex justify-center gap-2">
              <button
                type="button"
                onClick={() => handleRotate(-90)}
                disabled={isRotating}
                className="rounded-full border border-stone-300 px-4 py-1.5 text-sm transition hover:border-ink disabled:opacity-50"
              >
                ↺ Rotate left
              </button>
              <button
                type="button"
                onClick={() => handleRotate(90)}
                disabled={isRotating}
                className="rounded-full border border-stone-300 px-4 py-1.5 text-sm transition hover:border-ink disabled:opacity-50"
              >
                ↻ Rotate right
              </button>
            </div>

            {/* Actions */}
            <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleDownload}
                disabled={isDownloading}
                className="rounded-full bg-brand px-8 py-3 font-medium text-white transition hover:bg-brand-dark disabled:opacity-50"
              >
                {isDownloading ? 'Downloading...' : '⬇ Download image'}
              </button>
              <button
                type="button"
                onClick={handleTryAnotherItem}
                className="rounded-full border border-stone-300 px-8 py-3 font-medium transition hover:border-ink"
              >
                Try another item
              </button>
            </div>

            <p className="mt-3 text-center text-xs text-muted">
              Your result is stored on the server for about 1 hour, then deleted automatically.
            </p>

            <p className="mt-4 text-center text-xs text-muted">
              AI-generated preview of appearance only — not a guarantee of size or fit.
            </p>
          </div>
        )}
      </section>
    </div>
  )
}

export default TryOnPage
