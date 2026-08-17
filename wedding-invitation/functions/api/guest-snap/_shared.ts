const MAX_IMAGE_BYTES = 20 * 1024 * 1024
const SESSION_SECONDS = 24 * 60 * 60

const IMAGE_EXTENSIONS: Record<string, string> = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/webp': 'webp',
  'image/heic': 'heic',
  'image/heif': 'heif',
}

export type GuestPhotoRecord = {
  id: string
  object_key: string
  content_type: string
  guest_name: string | null
  message: string | null
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
  size_bytes: number
}

export type D1Statement = {
  bind: (...values: unknown[]) => D1Statement
  first: <T = unknown>() => Promise<T | null>
  all: <T = unknown>() => Promise<{ results: T[] }>
  run: () => Promise<unknown>
}

export type D1Database = { prepare: (query: string) => D1Statement }

export type R2ObjectBody = {
  body: ReadableStream
  httpEtag: string
  writeHttpMetadata: (headers: Headers) => void
}

export type R2Bucket = {
  put: (key: string, body: ReadableStream | ArrayBuffer, options?: unknown) => Promise<unknown>
  get: (key: string) => Promise<R2ObjectBody | null>
  delete: (key: string) => Promise<void>
}

export type GuestSnapEnv = {
  GUEST_SNAP_DB: D1Database
  GUEST_SNAP_BUCKET: R2Bucket
  TURNSTILE_SECRET_KEY?: string
  GUEST_SNAP_UPLOAD_OPENS_AT?: string
  GUEST_SNAP_ADMIN_PASSWORD: string
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

function encodeBase64Url(bytes: ArrayBuffer): string {
  const binary = Array.from(new Uint8Array(bytes), (byte) => String.fromCharCode(byte)).join('')
  return btoa(binary).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '')
}

function decodeBase64Url(value: string): ArrayBuffer {
  const normalized = value.replaceAll('-', '+').replaceAll('_', '/')
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
  return Uint8Array.from(atob(padded), (character) => character.charCodeAt(0)).buffer as ArrayBuffer
}

async function sessionKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign', 'verify'],
  )
}

export async function createAdminSession(secret: string, now = new Date()): Promise<string> {
  const expiresAt = Math.floor(now.getTime() / 1000) + SESSION_SECONDS
  const payload = String(expiresAt)
  const signature = await crypto.subtle.sign('HMAC', await sessionKey(secret), new TextEncoder().encode(payload))
  return `${payload}.${encodeBase64Url(signature)}`
}

export async function verifyAdminSession(token: string, secret: string, now = new Date()): Promise<boolean> {
  const [expiresAt, signature] = token.split('.')
  if (!expiresAt || !signature || Number(expiresAt) < Math.floor(now.getTime() / 1000)) return false
  try {
    return crypto.subtle.verify(
      'HMAC',
      await sessionKey(secret),
      decodeBase64Url(signature),
      new TextEncoder().encode(expiresAt),
    )
  } catch {
    return false
  }
}

export function readCookie(request: Request, name: string): string {
  const cookie = request.headers.get('Cookie') ?? ''
  const item = cookie.split(';').map((part) => part.trim()).find((part) => part.startsWith(`${name}=`))
  return item ? decodeURIComponent(item.slice(name.length + 1)) : ''
}

export async function isAdminRequest(request: Request, secret: string): Promise<boolean> {
  return verifyAdminSession(readCookie(request, 'guest_snap_admin'), secret)
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
