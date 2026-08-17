import { type FormEvent, useState } from 'react'

type AdminPhoto = {
  id: string
  guestName: string | null
  message: string | null
  status: 'pending' | 'approved' | 'rejected'
  createdAt: string
  sizeBytes: number
  mediaUrl: string
}

export function GuestSnapAdmin() {
  const [password, setPassword] = useState('')
  const [authenticated, setAuthenticated] = useState(false)
  const [photos, setPhotos] = useState<AdminPhoto[]>([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')

  const loadPhotos = async () => {
    const response = await fetch('/api/guest-snap/admin/photos', { headers: { Accept: 'application/json' } })
    if (!response.ok) throw new Error('사진 목록을 불러오지 못했습니다.')
    const data = await response.json() as { photos?: AdminPhoto[] }
    setPhotos(data.photos ?? [])
  }

  const login = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    const response = await fetch('/api/guest-snap/admin/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    })
    if (!response.ok) {
      setError('비밀번호를 확인해주세요.')
      return
    }
    setAuthenticated(true)
    setPassword('')
    try {
      await loadPhotos()
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '사진 목록을 불러오지 못했습니다.')
    }
  }

  const changeStatus = async (photo: AdminPhoto, status: 'approved' | 'rejected') => {
    setBusyId(photo.id)
    setError('')
    try {
      const response = await fetch(`/api/guest-snap/admin/photos/${photo.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status }),
      })
      if (!response.ok) throw new Error('사진 상태를 변경하지 못했습니다.')
      await loadPhotos()
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : '사진 상태를 변경하지 못했습니다.')
    } finally {
      setBusyId('')
    }
  }

  const deletePhoto = async (photo: AdminPhoto) => {
    if (!window.confirm('이 사진을 완전히 삭제할까요?')) return
    setBusyId(photo.id)
    setError('')
    try {
      const response = await fetch(`/api/guest-snap/admin/photos/${photo.id}`, { method: 'DELETE' })
      if (!response.ok) throw new Error('사진을 삭제하지 못했습니다.')
      setPhotos((current) => current.filter((item) => item.id !== photo.id))
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : '사진을 삭제하지 못했습니다.')
    } finally {
      setBusyId('')
    }
  }

  if (!authenticated) {
    return (
      <main className="guest-admin-shell">
        <section className="guest-admin-login">
          <p>GUEST SNAP</p>
          <h1>사진 관리</h1>
          <form onSubmit={(event) => void login(event)}>
            <label>
              <span>관리자 비밀번호</span>
              <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" />
            </label>
            <button type="submit" disabled={!password}>관리자 로그인</button>
          </form>
          {error && <p className="guest-admin-error" role="alert">{error}</p>}
          <a href="/">청첩장으로 돌아가기</a>
        </section>
      </main>
    )
  }

  return (
    <main className="guest-admin-shell">
      <header className="guest-admin-header">
        <div><p>GUEST SNAP</p><h1>사진 관리</h1></div>
        <button type="button" onClick={() => void loadPhotos()}>새로고침</button>
      </header>
      {error && <p className="guest-admin-error" role="alert">{error}</p>}
      <section className="guest-admin-grid" aria-label="게스트 스냅 검토 목록">
        {photos.map((photo) => (
          <article className="guest-admin-card" key={photo.id}>
            <img src={photo.mediaUrl} alt={`${photo.guestName || '익명'}님이 올린 사진`} />
            <div className="guest-admin-card-copy">
              <strong>{photo.guestName || '익명'}</strong>
              <span>{photo.status === 'pending' ? '검토 대기' : photo.status === 'approved' ? '공개 중' : '제외됨'}</span>
              {photo.message && <p>{photo.message}</p>}
              <small>{new Date(photo.createdAt).toLocaleString('ko-KR')}</small>
            </div>
            <div className="guest-admin-actions">
              <button type="button" disabled={busyId === photo.id} onClick={() => void changeStatus(photo, 'approved')} aria-label="사진 승인">승인</button>
              <button type="button" disabled={busyId === photo.id} onClick={() => void changeStatus(photo, 'rejected')} aria-label="사진 제외">제외</button>
              <button type="button" disabled={busyId === photo.id} onClick={() => void deletePhoto(photo)} aria-label="사진 삭제">삭제</button>
            </div>
          </article>
        ))}
        {photos.length === 0 && <p className="guest-admin-empty">아직 올라온 사진이 없습니다.</p>}
      </section>
    </main>
  )
}
