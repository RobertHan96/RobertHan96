const MAX_IMAGE_BYTES = 20 * 1024 * 1024

const IMAGE_EXTENSIONS: Record<string, string> = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/webp': 'webp',
  'image/heic': 'heic',
  'image/heif': 'heif',
}

export type R2Bucket = {
  put: (key: string, body: ReadableStream | ArrayBuffer, options?: unknown) => Promise<unknown>
}

export type GuestSnapEnv = {
  GUEST_SNAP_BUCKET: R2Bucket
  TURNSTILE_SECRET_KEY?: string
  VITE_GUEST_SNAP_UPLOAD_OPENS_AT?: string
}

export type PagesContext = {
  request: Request
  env: GuestSnapEnv
  params: Record<string, string | string[]>
}

export function json(data: unknown, status = 200, headers?: HeadersInit): Response {
  return Response.json(data, { status, headers })
}

export type UploadFile = {
  name: string
  type: string
  size: number
  stream: () => ReadableStream
}

export function isUploadFile(value: FormDataEntryValue | null): value is File & UploadFile {
  return typeof value !== 'string'
    && value !== null
    && typeof value.name === 'string'
    && typeof value.type === 'string'
    && typeof value.size === 'number'
    && typeof value.stream === 'function'
}

export function validateGuestImage(file: UploadFile): { ok: true; extension: string } | { ok: false; error: string } {
  if (file.size > MAX_IMAGE_BYTES) return { ok: false, error: '사진 한 장은 20MB 이하여야 합니다.' }
  const extension = IMAGE_EXTENSIONS[file.type.toLowerCase()]
  if (!extension) return { ok: false, error: '지원하지 않는 이미지 형식입니다.' }
  return { ok: true, extension }
}

export async function verifyTurnstile(request: Request, token: string, secret?: string): Promise<boolean> {
  const hostname = new URL(request.url).hostname
  if (!secret) return hostname === 'localhost' || hostname === '127.0.0.1'
  if (!token) return false

  const form = new FormData()
  form.set('secret', secret)
  form.set('response', token)
  const remoteIp = request.headers.get('CF-Connecting-IP')
  if (remoteIp) form.set('remoteip', remoteIp)

  const response = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    body: form,
  })
  if (!response.ok) return false
  const result = await response.json() as { success?: boolean }
  return result.success === true
}
