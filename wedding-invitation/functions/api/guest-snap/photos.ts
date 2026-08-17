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

export async function onRequestPost({ request, env }: PagesContext): Promise<Response> {
  const hostname = new URL(request.url).hostname
  const localRequest = hostname === 'localhost' || hostname === '127.0.0.1'
  const opensAt = env.VITE_GUEST_SNAP_UPLOAD_OPENS_AT ?? '2026-11-15T00:00:00+09:00'
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

  const id = crypto.randomUUID()
  const createdAt = new Date().toISOString()
  const objectKey = `guest-snap/${createdAt.slice(0, 10)}/${id}.${validation.extension}`

  await env.GUEST_SNAP_BUCKET.put(objectKey, photo.stream(), {
    httpMetadata: { contentType: photo.type, cacheControl: 'private, max-age=0' },
    customMetadata: { photoId: id, uploadedAt: createdAt },
  })

  return json({ ok: true, id }, 201)
}
