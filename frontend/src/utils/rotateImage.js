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

  const isSideways = degrees === 90 || degrees === 270
  const canvas = document.createElement('canvas')
  canvas.width = isSideways ? bitmap.height : bitmap.width
  canvas.height = isSideways ? bitmap.width : bitmap.height

  const context = canvas.getContext('2d')
  context.translate(canvas.width / 2, canvas.height / 2)
  context.rotate((degrees * Math.PI) / 180)
  context.drawImage(bitmap, -bitmap.width / 2, -bitmap.height / 2)
  bitmap.close()

  const supportedTypes = ['image/png', 'image/jpeg', 'image/webp']
  const fileType = supportedTypes.includes(originalBlob.type) ? originalBlob.type : 'image/png'

  const rotatedBlob = await new Promise((resolve) => canvas.toBlob(resolve, fileType, 0.95))
  return URL.createObjectURL(rotatedBlob)
}
