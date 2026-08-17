import {
  type GuestPhotoRecord,
  isAdminRequest,
  json,
  type PagesContext,
} from '../_shared'

export async function onRequestGet({ request, env, params }: PagesContext): Promise<Response> {
  const id = Array.isArray(params.id) ? params.id[0] : params.id
  if (!id) return json({ ok: false, error: '사진을 찾을 수 없습니다.' }, 404)

  const photo = await env.GUEST_SNAP_DB.prepare(`
    SELECT id, object_key, content_type, size_bytes, guest_name, message, status, created_at
    FROM guest_photos
    WHERE id = ?1
  `).bind(id).first<GuestPhotoRecord>()

  if (!photo) return json({ ok: false, error: '사진을 찾을 수 없습니다.' }, 404)
  if (photo.status !== 'approved' && !(await isAdminRequest(request, env.GUEST_SNAP_ADMIN_PASSWORD))) {
    return json({ ok: false, error: '사진을 찾을 수 없습니다.' }, 404)
  }

  const object = await env.GUEST_SNAP_BUCKET.get(photo.object_key)
  if (!object) return json({ ok: false, error: '사진 파일을 찾을 수 없습니다.' }, 404)

  const headers = new Headers()
  object.writeHttpMetadata(headers)
  headers.set('Content-Type', photo.content_type)
  headers.set('ETag', object.httpEtag)
  headers.set('Cache-Control', photo.status === 'approved' ? 'public, max-age=3600' : 'private, no-store')
  headers.set('X-Content-Type-Options', 'nosniff')
  return new Response(object.body, { headers })
}
