import {
  json,
  isUploadFile,
  type PagesContext,
  validateGuestImage,
  verifyTurnstile,
} from './_shared'

const MAX_PHOTOS_PER_REQUEST = 10

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

  const photoEntries = form.getAll('photo')
  if (!photoEntries.length) return json({ ok: false, error: '사진을 선택해주세요.' }, 400)
  if (photoEntries.length > MAX_PHOTOS_PER_REQUEST) {
    return json({ ok: false, error: `사진은 한 번에 최대 ${MAX_PHOTOS_PER_REQUEST}장까지 업로드할 수 있습니다.` }, 400)
  }

  const photos = photoEntries.filter(isUploadFile)
  if (photos.length !== photoEntries.length) return json({ ok: false, error: '사진을 선택해주세요.' }, 400)

  const validatedPhotos = photos.map((photo) => ({ photo, validation: validateGuestImage(photo) }))
  const invalidPhoto = validatedPhotos.find(({ validation }) => !validation.ok)
  if (invalidPhoto && !invalidPhoto.validation.ok) {
    return json({ ok: false, error: invalidPhoto.validation.error }, 400)
  }

  const createdAt = new Date().toISOString()
  const ids = validatedPhotos.map(() => crypto.randomUUID())

  try {
    await Promise.all(validatedPhotos.map(async ({ photo, validation }, index) => {
      if (!validation.ok) return
      const id = ids[index]
      const objectKey = `guest-snap/${createdAt.slice(0, 10)}/${id}.${validation.extension}`
      await env.GUEST_SNAP_BUCKET.put(objectKey, photo.stream(), {
        httpMetadata: { contentType: photo.type, cacheControl: 'private, max-age=0' },
        customMetadata: { photoId: id, uploadedAt: createdAt },
      })
    }))
  } catch (error) {
    console.error('Guest snap R2 upload failed', error)
    return json({ ok: false, error: '사진 저장에 실패했습니다. 잠시 후 다시 시도해주세요.' }, 503)
  }

  return json({ ok: true, id: ids[0], ids }, 201)
}
