import { isAdminRequest, json, type PagesContext } from '../_shared'

export async function onRequestGet({ request, env }: PagesContext): Promise<Response> {
  if (!(await isAdminRequest(request, env.GUEST_SNAP_ADMIN_PASSWORD))) {
    return json({ ok: false, error: '관리자 인증이 필요합니다.' }, 401)
  }

  const { results } = await env.GUEST_SNAP_DB.prepare(`
    SELECT id, guest_name, message, status, created_at, size_bytes
    FROM guest_photos
    ORDER BY created_at DESC
    LIMIT 300
  `).all<{
    id: string
    guest_name: string | null
    message: string | null
    status: string
    created_at: string
    size_bytes: number
  }>()

  return json({
    photos: results.map((photo) => ({
      id: photo.id,
      guestName: photo.guest_name,
      message: photo.message,
      status: photo.status,
      createdAt: photo.created_at,
      sizeBytes: photo.size_bytes,
      mediaUrl: `/api/guest-snap/media/${photo.id}?admin=1`,
    })),
  }, 200, { 'Cache-Control': 'no-store' })
}
