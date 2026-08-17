const SUPPORTED_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/heic',
  'image/heif',
])

export function isGuestSnapOpen(
  enabled: boolean,
  opensAt: string,
  now = new Date(),
  forceOpen = false,
): boolean {
  if (!enabled) return false
  return forceOpen || now.getTime() >= new Date(opensAt).getTime()
}

export function validateGuestFiles(files: File[], maxFiles: number, maxBytes: number) {
  const errors: string[] = []
  if (files.length > maxFiles) errors.push(`사진은 한 번에 최대 ${maxFiles}장까지 선택할 수 있습니다.`)

  const valid = files.slice(0, maxFiles).filter((file) => {
    if (!SUPPORTED_TYPES.has(file.type.toLowerCase())) {
      errors.push(`${file.name}: 지원하지 않는 형식입니다.`)
      return false
    }
    if (file.size > maxBytes) {
      errors.push(`${file.name}: 사진 한 장은 ${Math.floor(maxBytes / 1024 / 1024)}MB 이하여야 합니다.`)
      return false
    }
    return true
  })

  return { valid, errors }
}

export async function optimizeGuestImage(file: File, maxDimension = 2560): Promise<File> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return file
  if (typeof createImageBitmap !== 'function') return file

  try {
    const bitmap = await createImageBitmap(file)
    const scale = Math.min(1, maxDimension / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * scale))
    canvas.height = Math.max(1, Math.round(bitmap.height * scale))
    const context = canvas.getContext('2d')
    if (!context) {
      bitmap.close()
      return file
    }
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close()
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/webp', 0.88))
    if (!blob) return file
    const name = `${file.name.replace(/\.[^.]+$/, '') || 'guest-photo'}.webp`
    return new File([blob], name, { type: 'image/webp', lastModified: file.lastModified })
  } catch {
    return file
  }
}
