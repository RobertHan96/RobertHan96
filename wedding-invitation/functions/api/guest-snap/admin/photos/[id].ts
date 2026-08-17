import {
  type GuestPhotoRecord,
  isAdminRequest,
  json,
  type PagesContext,
} from '../../_shared'

function photoId(params: PagesContext['params']): string {
  const value = params.id
  return Array.isArray(value) ? value[0] : value ?? ''
}

async function requireAdmin({ request, env }: PagesContext): Promise<Response | null> {
  if (await isAdminRequest(request, env.GUEST_SNAP_ADMIN_PASSWORD)) return null
  return json({ ok: false, error: '관리자 인증이 필요합니다.' }, 401)
}

export async function onRequestPatch(context: PagesContext): Promise<Response> {
  const unauthorized = await requireAdmin(context)
  if (unauthorized) return unauthorized

  const id = photoId(context.params)
  const body = await context.request.json().catch(() => ({})) as { status?: unknown }
  if (body.status !== 'approved' && body.status !== 'rejected') {
    return json({ ok: false, error: '승인 또는 제외 상태만 선택할 수 있습니다.' }, 400)
  }

  await context.env.GUEST_SNAP_DB.prepare(`
    UPDATE guest_photos
    SET status = ?1, reviewed_at = ?2
    WHERE id = ?3
  `).bind(body.status, new Date().toISOString(), id).run()

  return json({ ok: true, id, status: body.status })
}

export async function onRequestDelete(context: PagesContext): Promise<Response> {
  const unauthorized = await requireAdmin(context)
  if (unauthorized) return unauthorized

  const id = photoId(context.params)
  const photo = await context.env.GUEST_SNAP_DB.prepare(`
    SELECT id, object_key, content_type, size_bytes, guest_name, message, status, created_at
    FROM guest_photos
    WHERE id = ?1
  `).bind(id).first<GuestPhotoRecord>()
  if (!photo) return json({ ok: false, error: '사진을 찾을 수 없습니다.' }, 404)

  await context.env.GUEST_SNAP_BUCKET.delete(photo.object_key)
  await context.env.GUEST_SNAP_DB.prepare('DELETE FROM guest_photos WHERE id = ?1').bind(id).run()
  return json({ ok: true, id })
}
