import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { create3DModel, createTryOn, downloadImage, getProducts } from '../services/api.js'
import BeforeAfterComparison from '../components/BeforeAfterComparison.jsx'
import { rotateImage } from '../utils/rotateImage.js'
import PhotoUploader from '../components/PhotoUploader.jsx'
import ProductCard from '../components/ProductCard.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

const Model3DViewer = lazy(() => import('../components/Model3DViewer.jsx'))

const ALLOWED_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_PHOTO_SIZE_MB = 10

function TryOnPage() {
  const [searchParams] = useSearchParams()
  const productFromAddress = searchParams.get('product')

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
  const [isCreating3D, setIsCreating3D] = useState(false)   // true while the 3D AI works
  const [model3DError, setModel3DError] = useState('')

  const resultSectionRef = useRef(null)

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

  useEffect(() => {
    return () => {
      if (photoPreviewUrl) {
        URL.revokeObjectURL(photoPreviewUrl)
      }
    }
  }, [photoPreviewUrl])

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
    setPhotoPreviewUrl(URL.createObjectURL(file))
    setTryOnResult(null) // a new photo means the old result no longer applies
  }

  function handleProductSelected(product) {
    setSelectedProductId(product.id)
    setTryOnResult(null)
    setErrorMessage('')
  }

  async function handleGenerate() {
    setErrorMessage('')
    setTryOnResult(null)
    setIsGenerating(true)

    resultSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })

    try {
      const result = await createTryOn(photoFile, selectedProductId)
      setTryOnResult(result)
    } catch (error) {
      setErrorMessage(error.message)
    } finally {
      setIsGenerating(false)
    }
  }

  async function handleRotate(direction) {
    const currentRotation = tryOnResult.rotation || 0
    const newRotation = (currentRotation + direction + 360) % 360

    setIsRotating(true)
    try {
      let rotatedUrl = null
      if (newRotation !== 0) {
        rotatedUrl = await rotateImage(tryOnResult.result_url, newRotation)
      }
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

  async function handleCreate3DModel() {
    const resultUrl = tryOnResult.result_url
    setModel3DError('')
    setIsCreating3D(true)
    try {
      const model = await create3DModel(tryOnResult.rotated_url || resultUrl)
      setTryOnResult((currentResult) => {
        if (currentResult && currentResult.result_url === resultUrl) {
          return { ...currentResult, model_url: model.model_url }
        }
        return currentResult
      })
    } catch (error) {
      setModel3DError(error.message)
    } finally {
      setIsCreating3D(false)
    }
  }

  async function handleDownload() {
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

  function handleTryAnotherItem() {
    setSelectedProductId(null)
    setTryOnResult(null)
    setErrorMessage('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleReset() {
    setPhotoFile(null)
    setPhotoPreviewUrl(null)
    setSelectedProductId(null)
    setTryOnResult(null)
    setErrorMessage('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const selectedProduct = products.find((product) => product.id === selectedProductId)
  const canGenerate = photoFile !== null && selectedProduct !== undefined && !isGenerating

  let generateHint = 'Ready! Click Generate to see the result.'
  if (!photoFile && !selectedProduct) {
    generateHint = 'Upload a photo and select a garment to continue.'
  } else if (!photoFile) {
    generateHint = 'Upload a photo of yourself to continue.'
  } else if (!selectedProduct) {
    generateHint = 'Select a garment to continue.'
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">Virtual Try-On</h1>
      <p className="mt-2 text-muted">Upload your photo, pick a garment and let the AI do the rest.</p>

      <div className="mt-8 grid gap-8 lg:grid-cols-3">
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

            {tryOnResult.mock_mode && (
              <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-800">
                Mock mode is ON: the photo is returned unchanged and no AI credits are used.
                Set TRYON_MOCK_MODE=false in backend/.env for real AI results.
              </p>
            )}

            <div className="mt-6">
              <BeforeAfterComparison
                beforeUrl={photoPreviewUrl}
                afterUrl={tryOnResult.rotated_url || tryOnResult.result_url}
              />
            </div>

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

            <div className="mt-8 border-t border-stone-200 pt-6">
              <h3 className="text-center font-display text-xl font-semibold">View in 3D (beta)</h3>

              {!tryOnResult.model_url && !isCreating3D && (
                <div className="mt-3 text-center">
                  <button
                    type="button"
                    onClick={handleCreate3DModel}
                    className="mt-4 rounded-full bg-ink px-8 py-3 font-medium text-white transition hover:opacity-90"
                  >
                    Create 3D model
                  </button>
                </div>
              )}

              {isCreating3D && (
                <LoadingSpinner message="Building your 3D model... this usually takes 1–3 minutes. Please keep this page open." />
              )}

              {model3DError && !isCreating3D && (
                <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-center text-sm text-red-700">{model3DError}</p>
              )}

              {tryOnResult.model_url && (
                <div className="mt-4">
                  <Suspense fallback={<LoadingSpinner message="Loading the 3D viewer..." />}>
                    <Model3DViewer modelUrl={tryOnResult.model_url} />
                  </Suspense>
                  <div className="mt-3 text-center">
                    <button
                      type="button"
                      onClick={() => downloadImage(tryOnResult.model_url, `virtual-tryon-${tryOnResult.product_id}.glb`).catch((error) => setModel3DError(error.message))}
                      className="rounded-full border border-stone-300 px-6 py-2 text-sm transition hover:border-ink"
                    >
                      ⬇ Download 3D model (.glb)
                    </button>
                  </div>
                </div>
              )}
            </div>

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
