const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

const TRYON_TIMEOUT_MS = 180000

// Turn a failed response into a readable error message.
async function readErrorMessage(response) {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
  }
  return `Something went wrong (error ${response.status}). Please try again.`
}

// GET /products — load the clothing catalog.
export async function getProducts() {
  let response
  try {
    response = await fetch(`${API_URL}/products`)
  } catch {
    throw new Error(`Cannot reach the backend at ${API_URL}. It may be starting up (wait 1 minute and refresh), or the address is wrong.`)
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response))
  }
  return response.json()
}

// Shared request helper for the Manage Products functions.
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

// POST /products — add a new product (Manage Products page).
export async function createProduct(productDetails, imageFile) {
  const formData = new FormData()
  formData.append('name', productDetails.name)
  formData.append('category', productDetails.category)
  formData.append('price', productDetails.price)
  formData.append('description', productDetails.description)
  formData.append('image', imageFile)

  return sendRequest(`${API_URL}/products`, { method: 'POST', body: formData })
}

// PUT /products/{id}/image — upload or replace a product's garment image.
export async function uploadProductImage(productId, imageFile) {
  const formData = new FormData()
  formData.append('image', imageFile)

  return sendRequest(`${API_URL}/products/${productId}/image`, { method: 'PUT', body: formData })
}

// DELETE /products/{id} — delete a product and its image.
export async function deleteProduct(productId) {
  return sendRequest(`${API_URL}/products/${productId}`, { method: 'DELETE' })
}

// Download a file. A plain <a download> doesn't work for files on another domain, so we fetch it as a blob.
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

// POST /tryon — send the user's photo and chosen product to the backend.
export async function createTryOn(photoFile, productId) {
  const formData = new FormData()
  formData.append('person_image', photoFile)
  formData.append('product_id', productId)

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

const MODEL3D_TIMEOUT_MS = 6 * 60 * 1000 // 6 minutes

// POST /model3d — turn an image into a rotatable 3D model.
export async function create3DModel(imageUrl) {
  let imageBlob
  try {
    const imageResponse = await fetch(imageUrl)
    if (!imageResponse.ok) {
      throw new Error()
    }
    imageBlob = await imageResponse.blob()
  } catch {
    throw new Error('The result image is no longer available. Please generate the try-on again.')
  }

  const formData = new FormData()
  formData.append('image', imageBlob, 'tryon-result.jpg')

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), MODEL3D_TIMEOUT_MS)

  let response
  try {
    response = await fetch(`${API_URL}/model3d`, {
      method: 'POST',
      body: formData,
      signal: controller.signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The 3D model took too long. The free service may be busy; please try again later.')
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
