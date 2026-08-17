CREATE TABLE IF NOT EXISTS guest_photos (
  id TEXT PRIMARY KEY,
  object_key TEXT NOT NULL UNIQUE,
  content_type TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  guest_name TEXT,
  message TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  created_at TEXT NOT NULL,
  reviewed_at TEXT,
  ip_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_guest_photos_status_created
  ON guest_photos(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_guest_photos_rate_limit
  ON guest_photos(ip_hash, created_at DESC);
