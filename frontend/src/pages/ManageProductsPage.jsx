// TODO (Phase 2): protect this page with an admin login.

import { useEffect, useState } from 'react'

import { createProduct, deleteProduct, getProducts, uploadProductImage } from '../services/api.js'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorMessage from '../components/ErrorMessage.jsx'

// TODO: Add more product categories here (shown as suggestions in the form).
const SUGGESTED_CATEGORIES = ['T-Shirts', 'Shirts', 'Hoodies', 'Dresses', 'Jackets', 'Tops']

const EMPTY_FORM = { name: '', category: '', price: '', description: '' }

function ManageProductsPage() {
  const [products, setProducts] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  const [busyProductId, setBusyProductId] = useState(null)

  const [formValues, setFormValues] = useState(EMPTY_FORM)
  const [newImageFile, setNewImageFile] = useState(null)
  const [isAdding, setIsAdding] = useState(false)
  const [fileInputKey, setFileInputKey] = useState(0)

  async function loadProducts() {
    try {
      const loadedProducts = await getProducts()
      setProducts(loadedProducts)
    } catch (error) {
      setErrorMessage(error.message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    getProducts()
      .then((loadedProducts) => setProducts(loadedProducts))
      .catch((error) => setErrorMessage(error.message))
      .finally(() => setIsLoading(false))
  }, [])

  function showSuccess(message) {
    setErrorMessage('')
    setSuccessMessage(message)
  }

  function showError(message) {
    setSuccessMessage('')
    setErrorMessage(message)
  }

  async function handleImageChosen(product, event) {
    const imageFile = event.target.files[0]
    event.target.value = '' // allow choosing the same file again later
    if (!imageFile) {
      return
    }

    setBusyProductId(product.id)
    try {
      await uploadProductImage(product.id, imageFile)
      showSuccess(`Image for "${product.name}" uploaded.`)
      await loadProducts()
    } catch (error) {
      showError(error.message)
    } finally {
      setBusyProductId(null)
    }
  }

  async function handleDelete(product) {
    const userIsSure = window.confirm(`Delete "${product.name}"? This cannot be undone.`)
    if (!userIsSure) {
      return
    }

    setBusyProductId(product.id)
    try {
      await deleteProduct(product.id)
      showSuccess(`"${product.name}" was deleted.`)
      await loadProducts()
    } catch (error) {
      showError(error.message)
    } finally {
      setBusyProductId(null)
    }
  }

  function handleFormChange(event) {
    const fieldName = event.target.name
    const fieldValue = event.target.value
    setFormValues({ ...formValues, [fieldName]: fieldValue })
  }

  async function handleAddProduct(event) {
    event.preventDefault()

    if (!newImageFile) {
      showError('Please choose an image for the new product.')
      return
    }

    setIsAdding(true)
    try {
      const newProduct = await createProduct(formValues, newImageFile)
      showSuccess(`"${newProduct.name}" was added to the catalog.`)
      setFormValues(EMPTY_FORM)
      setNewImageFile(null)
      setFileInputKey(fileInputKey + 1)
      await loadProducts()
    } catch (error) {
      showError(error.message)
    } finally {
      setIsAdding(false)
    }
  }

  const inputClasses =
    'mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm focus:border-brand focus:outline-none'

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="font-display text-3xl font-semibold sm:text-4xl">Manage Products</h1>
      <p className="mt-2 text-muted">Upload garment images and add or remove products.</p>

      <div className="mt-6 rounded-xl border border-stone-200 bg-white p-4 text-sm text-muted">
        <p className="font-medium text-ink">Tips for good garment images</p>
        <ul className="mt-1 list-inside list-disc space-y-0.5">
          <li>One garment per image, front view, nothing cut off.</li>
          <li>Flat-lay or on a mannequin/model, plain light background.</li>
          <li>JPEG, PNG or WebP, under 10 MB. Only use images you have the right to use.</li>
        </ul>
      </div>

      <div className="mt-6 space-y-3">
        <ErrorMessage message={errorMessage} onDismiss={() => setErrorMessage('')} />
        {successMessage && (
          <p role="status" className="rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
            {successMessage}
          </p>
        )}
      </div>

      <div className="mt-8 grid gap-10 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <h2 className="font-display text-xl font-semibold">Current products</h2>

          {isLoading && <LoadingSpinner message="Loading products..." />}

          <ul className="mt-4 space-y-3">
            {products.map((product) => {
              const isBusy = busyProductId === product.id
              return (
                <li
                  key={product.id}
                  className="flex items-center gap-4 rounded-xl border border-stone-200 bg-white p-3"
                >
                  <div className="h-20 w-16 shrink-0 overflow-hidden rounded-lg bg-stone-100">
                    {product.image_available ? (
                      <img src={product.image_url} alt={product.name} className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex h-full items-center justify-center text-[10px] text-red-600">
                        No image
                      </div>
                    )}
                  </div>

                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{product.name}</p>
                    <p className="text-xs text-muted">
                      {product.category} · {product.price}
                    </p>
                  </div>

                  <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
                    <label
                      className={`cursor-pointer rounded-full bg-brand px-3 py-1.5 text-center text-xs font-medium text-white hover:bg-brand-dark ${
                        isBusy ? 'pointer-events-none opacity-50' : ''
                      }`}
                    >
                      {isBusy ? 'Saving...' : product.image_available ? 'Replace image' : 'Upload image'}
                      <input
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        className="hidden"
                        onChange={(event) => handleImageChosen(product, event)}
                      />
                    </label>
                    <button
                      type="button"
                      onClick={() => handleDelete(product)}
                      disabled={isBusy}
                      className="rounded-full border border-stone-300 px-3 py-1.5 text-xs text-red-700 hover:border-red-400 disabled:opacity-50"
                    >
                      Delete
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        </section>

        <section>
          <h2 className="font-display text-xl font-semibold">Add a new product</h2>

          <form onSubmit={handleAddProduct} className="mt-4 space-y-4 rounded-xl border border-stone-200 bg-white p-4">
            <label className="block text-sm">
              Name *
              <input name="name" required value={formValues.name} onChange={handleFormChange} className={inputClasses} placeholder="e.g. Denim Jacket" />
            </label>

            <label className="block text-sm">
              Category *
              <input name="category" required list="category-suggestions" value={formValues.category} onChange={handleFormChange} className={inputClasses} placeholder="e.g. Jackets" />
              <datalist id="category-suggestions">
                {SUGGESTED_CATEGORIES.map((category) => (
                  <option key={category} value={category} />
                ))}
              </datalist>
            </label>

            <label className="block text-sm">
              Price *
              <input name="price" type="number" required min="0" step="0.01" value={formValues.price} onChange={handleFormChange} className={inputClasses} placeholder="e.g. 39.99" />
            </label>

            <label className="block text-sm">
              Description
              <textarea name="description" rows="3" value={formValues.description} onChange={handleFormChange} className={inputClasses} placeholder="Colour, material, fit... (helps the AI)" />
            </label>

            <label className="block text-sm">
              Garment image *
              <input
                key={fileInputKey}
                type="file"
                required
                accept="image/jpeg,image/png,image/webp"
                onChange={(event) => setNewImageFile(event.target.files[0] || null)}
                className="mt-1 block w-full text-sm file:mr-3 file:rounded-full file:border-0 file:bg-brand-light file:px-3 file:py-1.5 file:text-brand-dark"
              />
            </label>

            <button
              type="submit"
              disabled={isAdding}
              className="w-full rounded-full bg-brand px-4 py-2.5 font-medium text-white hover:bg-brand-dark disabled:opacity-50"
            >
              {isAdding ? 'Adding...' : 'Add product'}
            </button>
          </form>
        </section>
      </div>
    </div>
  )
}

export default ManageProductsPage
