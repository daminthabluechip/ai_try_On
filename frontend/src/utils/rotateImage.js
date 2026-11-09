// =====================================================================
// rotateImage.js  —  make a rotated copy of an image, in the browser.
// =====================================================================
// Why a real copy (and not just CSS "rotate")?
//   CSS only changes how the picture LOOKS on screen. The downloaded file
//   would still be the old, un-rotated image. Drawing the image onto a
//   <canvas> creates a NEW image that is truly rotated, so the download
//   matches what the user sees.
//
// How it works:
//   1. download the image as raw data (a "blob"),
//   2. draw it rotated onto an invisible <canvas>,
//   3. turn the canvas into a new image and give it a temporary address.
//
// We always rotate from the ORIGINAL result (not from an already-rotated
// copy), so the quality never gets worse after many clicks.

/**
 * Return a temporary address (blob URL) of `imageUrl` rotated clockwise
 * by `degrees` (0, 90, 180 or 270).
 */
export async function rotateImage(imageUrl, degrees) {
  let response
  try {
    response = await fetch(imageUrl)
  } catch {
    throw new Error('Cannot reach the server to rotate the image.')
  }
  if (!response.ok) {
    throw new Error('The image is no longer available. Please generate it again.')
  }

  const originalBlob = await response.blob()
  const bitmap = await createImageBitmap(originalBlob)

  // Turning 90° or 270° swaps width and height.
  const isSideways = degrees === 90 || degrees === 270
  const canvas = document.createElement('canvas')
  canvas.width = isSideways ? bitmap.height : bitmap.width
  canvas.height = isSideways ? bitmap.width : bitmap.height

  // Move the drawing point to the centre, rotate there, then draw the
  // image centred on that point.
  const context = canvas.getContext('2d')
  context.translate(canvas.width / 2, canvas.height / 2)
  context.rotate((degrees * Math.PI) / 180)
  context.drawImage(bitmap, -bitmap.width / 2, -bitmap.height / 2)
  bitmap.close()

  // Keep the original file type (PNG / JPEG / WebP) when possible.
  const supportedTypes = ['image/png', 'image/jpeg', 'image/webp']
  const fileType = supportedTypes.includes(originalBlob.type) ? originalBlob.type : 'image/png'

  const rotatedBlob = await new Promise((resolve) => canvas.toBlob(resolve, fileType, 0.95))
  return URL.createObjectURL(rotatedBlob)
}
