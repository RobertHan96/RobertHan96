import {
  json,
  isUploadFile,
  type PagesContext,
  validateGuestImage,
  verifyTurnstile,
} from './_shared'

function optionalText(value: FormDataEntryValue | null, maxLength: number): string | null {
  if (typeof value !== 'string') return null
  const trimmed = value.trim().slice(0, maxLength)
  return trimmed || null
}

async function hashAddress(address: string, salt: string): Promise<string> {
  const data = new TextEncoder().encode(`${salt}:${address}`)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('')
}

export async function onRequestPost({ request, env }: PagesContext): Promise<Response> {
  const hostname = new URL(request.url).hostname
  const localRequest = hostname === 'localhost' || hostname === '127.0.0.1'
  const opensAt = env.GUEST_SNAP_UPLOAD_OPENS_AT ?? '2026-11-15T00:00:00+09:00'
  if (!localRequest && Date.now() < new Date(opensAt).getTime()) {
    return json({ ok: false, error: '게스트 스냅은 예식 당일부터 열립니다.' }, 403)
  }

  let form: FormData
  try {
    form = await request.formData()
  } catch {
    return json({ ok: false, error: '업로드 요청을 읽을 수 없습니다.' }, 400)
  }

  const token = optionalText(form.get('turnstileToken'), 2048) ?? ''
  if (!(await verifyTurnstile(request, token, env.TURNSTILE_SECRET_KEY))) {
    return json({ ok: false, error: '사람인지 확인하지 못했습니다. 다시 시도해주세요.' }, 403)
  }

  const photo = form.get('photo')
  if (!isUploadFile(photo)) return json({ ok: false, error: '사진을 선택해주세요.' }, 400)

  const validation = validateGuestImage(photo)
  if (!validation.ok) return json({ ok: false, error: validation.error }, 400)

  const addressHash = await hashAddress(
    request.headers.get('CF-Connecting-IP') ?? 'unknown',
    env.GUEST_SNAP_ADMIN_PASSWORD,
  )
  const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString()
  const recent = await env.GUEST_SNAP_DB.prepare(`
    SELECT COUNT(*) AS count
    FROM guest_photos
    WHERE ip_hash = ?1 AND created_at >= ?2
  `).bind(addressHash, oneHourAgo).first<{ count: number }>()
  if ((recent?.count ?? 0) >= 30) {
    return json({ ok: false, error: '한 시간 동안 올릴 수 있는 사진 수를 초과했습니다.' }, 429)
  }

  const id = crypto.randomUUID()
  const createdAt = new Date().toISOString()
  const objectKey = `guest-snap/${createdAt.slice(0, 10)}/${id}.${validation.extension}`
  const guestName = optionalText(form.get('guestName'), 40)
  const message = optionalText(form.get('message'), 300)

  await env.GUEST_SNAP_BUCKET.put(objectKey, photo.stream(), {
    httpMetadata: { contentType: photo.type, cacheControl: 'private, max-age=0' },
    customMetadata: { photoId: id, uploadedAt: createdAt },
  })

  try {
    await env.GUEST_SNAP_DB.prepare(`
      INSERT INTO guest_photos (
        id, object_key, content_type, size_bytes, guest_name, message, status, created_at, ip_hash
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9)
    `).bind(
      id,
      objectKey,
      photo.type,
      photo.size,
      guestName,
      message,
      'pending',
      createdAt,
      addressHash,
    ).run()
  } catch (error) {
    await env.GUEST_SNAP_BUCKET.delete(objectKey)
    throw error
  }

  return json({ ok: true, id, status: 'pending' }, 201)
}

export async function onRequestGet({ env }: PagesContext): Promise<Response> {
  const { results } = await env.GUEST_SNAP_DB.prepare(`
    SELECT id, guest_name, message, created_at
    FROM guest_photos
    WHERE status = 'approved'
    ORDER BY created_at DESC
    LIMIT 100
  `).all<{
    id: string
    guest_name: string | null
    message: string | null
    created_at: string
  }>()

  return json({
    photos: results.map((photo) => ({
      id: photo.id,
      guestName: photo.guest_name,
      message: photo.message,
      createdAt: photo.created_at,
      mediaUrl: `/api/guest-snap/media/${photo.id}`,
    })),
  }, 200, { 'Cache-Control': 'no-store' })
}
