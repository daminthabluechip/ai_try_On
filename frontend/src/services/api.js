// =====================================================================
// services/api.js  —  the ONLY file that talks to the backend.
// =====================================================================
// Pages never call fetch() themselves; they call the functions below.
// So if the backend address or an endpoint changes, you edit only here.
//
// IMPORTANT: there is NO API key in the frontend. Anything in this
// folder can be seen by website visitors (F12 -> Sources). The key lives
// only in backend/.env, and only the backend talks to the AI provider.

// Address of the FastAPI backend.
// It can be set in frontend/.env as VITE_API_URL (needed when you deploy).
// If it isn't set, we use the local development address.
// .replace(/\/+$/, '') removes a trailing "/" so we never build "...com//products".
const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

// The AI usually needs ~10-20 seconds. We give up after 3 minutes.
const TRYON_TIMEOUT_MS = 180000


/**
 * Turn a failed response into a readable error message.
 * Our FastAPI backend sends errors as JSON: { "detail": "message" }.
 */
async function readErrorMessage(response) {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // The body wasn't JSON — fall through to the generic message below.
  }
  return `Something went wrong (error ${response.status}). Please try again.`
}


/**
 * GET /products — load the clothing catalog.
 * Returns an array of product objects.
 */
export async function getProducts() {
  let response
  try {
    response = await fetch(`${API_URL}/products`)
  } catch {
    // fetch() itself fails when the backend is not running at all.
    throw new Error(`Cannot reach the backend at ${API_URL}. It may be starting up (wait 1 minute and refresh), or the address is wrong.`)
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }
  return response.json()
}


/**
 * Small helper used by the "Manage Products" functions below:
 * sends a request and returns the JSON answer, or throws a readable error.
 */
async function sendRequest(url, options) {
  let response
  try {
    response = await fetch(url, options)
  } catch {
    throw new Error(`Cannot reach the backend at ${API_URL}. It may be starting up (wait 1 minute and refresh), or the address is wrong.`)
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }
  return response.json()
}


/**
 * POST /products — add a new product (Manage Products page).
 * productDetails -> { name, category, price, description }
 * imageFile      -> the garment image (File object)
 */
export async function createProduct(productDetails, imageFile) {
  const formData = new FormData()
  formData.append('name', productDetails.name)
  formData.append('category', productDetails.category)
  formData.append('price', productDetails.price)
  formData.append('description', productDetails.description)
  formData.append('image', imageFile)

  return sendRequest(`${API_URL}/products`, { method: 'POST', body: formData })
}


/**
 * PUT /products/{id}/image — upload or replace a product's garment image.
 */
export async function uploadProductImage(productId, imageFile) {
  const formData = new FormData()
  formData.append('image', imageFile)

  return sendRequest(`${API_URL}/products/${productId}/image`, { method: 'PUT', body: formData })
}


/**
 * DELETE /products/{id} — delete a product and its image.
 */
export async function deleteProduct(productId) {
  return sendRequest(`${API_URL}/products/${productId}`, { method: 'DELETE' })
}


/**
 * Download an image to the user's computer.
 *
 * Why not a simple <a href="..." download>?  Browsers ignore the "download"
 * attribute for images from a DIFFERENT address (our backend runs on port
 * 8000, the website on 5173) and just open the image instead. So we:
 *   1. fetch the image as a "blob" (raw file data),
 *   2. create a temporary local address for it,
 *   3. click an invisible download link,
 *   4. release the temporary address.
 */
export async function downloadImage(imageUrl, fileName) {
  let response
  try {
    response = await fetch(imageUrl)
  } catch {
    throw new Error('Cannot reach the server to download the image.')
  }
  if (!response.ok) {
    throw new Error('The image is no longer available. Please generate it again.')
  }

  const imageBlob = await response.blob()
  const temporaryUrl = URL.createObjectURL(imageBlob)

  const link = document.createElement('a')
  link.href = temporaryUrl
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()

  URL.revokeObjectURL(temporaryUrl)
}


/**
 * POST /tryon — send the user's photo and chosen product to the backend.
 *
 * photoFile -> the File object from the <input type="file">
 * productId -> e.g. "black-tshirt"
 *
 * Returns: { result_url, product_id, product_name, mock_mode }
 */
export async function createTryOn(photoFile, productId) {
  // FormData builds a "multipart/form-data" request — the standard way
  // to upload files. The field names must match the backend
  // (routes/tryon.py: person_image and product_id).
  const formData = new FormData()
  formData.append('person_image', photoFile)
  formData.append('product_id', productId)

  // AbortController lets us cancel the request if it takes too long.
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), TRYON_TIMEOUT_MS)

  let response
  try {
    response = await fetch(`${API_URL}/tryon`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The try-on took too long. Please try again.')
    }
    throw new Error(`Cannot reach the backend at ${API_URL}. It may be starting up (wait 1 minute and refresh), or the address is wrong.`)
  } finally {
    clearTimeout(timeoutId)
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }
  return response.json()
}
