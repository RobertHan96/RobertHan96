import { createAdminSession, json } from '../_shared'

type SessionContext = {
  request: Request
  env: { GUEST_SNAP_ADMIN_PASSWORD: string }
}

export async function onRequestPost({ request, env }: SessionContext): Promise<Response> {
  let password = ''
  try {
    const body = await request.json() as { password?: unknown }
    if (typeof body.password === 'string') password = body.password
  } catch {
    return json({ ok: false, error: '요청 형식이 올바르지 않습니다.' }, 400)
  }

  if (!env.GUEST_SNAP_ADMIN_PASSWORD || password !== env.GUEST_SNAP_ADMIN_PASSWORD) {
    return json({ ok: false, error: '비밀번호가 올바르지 않습니다.' }, 401)
  }

  const token = await createAdminSession(env.GUEST_SNAP_ADMIN_PASSWORD)
  const secure = new URL(request.url).protocol === 'https:' ? '; Secure' : ''
  return json({ ok: true }, 200, {
    'Set-Cookie': `guest_snap_admin=${encodeURIComponent(token)}; Path=/; Max-Age=86400; HttpOnly; SameSite=Strict${secure}`,
    'Cache-Control': 'no-store',
  })
}
