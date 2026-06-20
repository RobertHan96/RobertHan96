export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "GET") {
      if (url.pathname === "/logs") {
        return handleLogRead(request, env, url);
      }
      return json({ ok: true, status: "healthy" });
    }

    if (request.method !== "POST") {
      return json({ ok: false, error: "method_not_allowed" }, 405);
    }

    if (url.pathname === "/log") {
      return handleLogWrite(request, env);
    }

    if (url.pathname === "/job-fit-report") {
      return handleJobFitReport(request, env);
    }

    if (url.pathname === "/state/get") {
      return handleStateGet(request, env);
    }

    if (url.pathname === "/state/put") {
      return handleStatePut(request, env);
    }

    const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if (!secret || secret !== env.TELEGRAM_WEBHOOK_SECRET_TOKEN) {
      return json({ ok: false, error: "invalid_secret" }, 401);
    }

    const update = await request.json();
    await maybeStoreInboxLog(env, update);

    const repository = env.GITHUB_REPOSITORY;
    const githubToken = env.GITHUB_TOKEN;
    if (!repository || !githubToken) {
      return json({ ok: false, error: "missing_github_config" }, 500);
    }

    const response = await fetch(`https://api.github.com/repos/${repository}/dispatches`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${githubToken}`,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "telegram-memory-worker",
      },
      body: JSON.stringify({
        event_type: "telegram-memory-update",
        client_payload: {
          received_at: new Date().toISOString(),
          update,
        },
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      return json({ ok: false, error: "github_dispatch_failed", body }, 500);
    }

    return json({ ok: true });
  },
};

async function handleLogWrite(request, env) {
  const authorized = authorizeBridge(request, env);
  if (!authorized) {
    return json({ ok: false, error: "unauthorized" }, 401);
  }

  const namespace = getKvNamespace(env);
  if (!namespace) {
    return json({ ok: false, error: "missing_kv_namespace" }, 500);
  }

  const payload = await request.json();
  const kind = sanitizeKind(payload.kind || "outbox");
  const logDate = sanitizeDate(payload.date || new Date().toISOString().slice(0, 10));
  const storageKey = await buildStorageKey(
    kind,
    logDate,
    payload.message || payload.text || payload.title || "log",
  );

  await namespace.put(storageKey, JSON.stringify(payload), {
    expirationTtl: 60 * 60 * 24 * 14,
  });

  return json({ ok: true, key: storageKey });
}

async function handleLogRead(request, env, url) {
  const authorized = authorizeBridge(request, env);
  if (!authorized) {
    return json({ ok: false, error: "unauthorized" }, 401);
  }

  const namespace = getKvNamespace(env);
  if (!namespace) {
    return json({ ok: false, error: "missing_kv_namespace" }, 500);
  }

  const kind = sanitizeKind(url.searchParams.get("kind") || "outbox");
  const logDate = sanitizeDate(url.searchParams.get("date") || new Date().toISOString().slice(0, 10));
  const prefix = `${kind}:${logDate}:`;
  const listed = await namespace.list({ prefix, limit: 1000 });

  const items = await Promise.all(
    listed.keys.map(async (key) => {
      const value = await namespace.get(key.name, "text");
      if (!value) {
        return null;
      }
      try {
        return JSON.parse(value);
      } catch {
        return null;
      }
    }),
  );

  const logs = items.filter(Boolean).sort((a, b) => {
    const aTime = a?.sent_at || a?.received_at || "";
    const bTime = b?.sent_at || b?.received_at || "";
    return aTime.localeCompare(bTime);
  });
  return json({ ok: true, kind, date: logDate, logs });
}

async function handleJobFitReport(request, env) {
  const authorized = authorizeBridge(request, env);
  if (!authorized) {
    return json({ ok: false, error: "unauthorized" }, 401);
  }

  const bucket = env.JOB_FIT_REPORTS_BUCKET;
  if (!bucket) {
    return json({ ok: false, error: "missing_job_fit_bucket" }, 500);
  }

  const payload = await request.json();
  const report = String(payload.report || "");
  if (!report.trim()) {
    return json({ ok: false, error: "empty_report" }, 400);
  }

  const date = sanitizeDate(payload.date || new Date().toISOString().slice(0, 10));
  const filename = sanitizeFilename(payload.filename || `job_report_${Date.now()}.md`);
  const key = `jobs/reports/${date}/${filename}`;

  await bucket.put(key, report, {
    httpMetadata: {
      contentType: "text/markdown; charset=utf-8",
    },
    customMetadata: {
      generated_at: String(payload.generated_at || ""),
      high_fit_count: String((payload.high_fit_titles || []).length || 0),
    },
  });

  return json({ ok: true, key });
}

function authorizeBridge(request, env) {
  const token = request.headers.get("Authorization")?.replace(/^Bearer\s+/i, "") || "";
  const validTokens = [
    env.TELEGRAM_MEMORY_BRIDGE_TOKEN,
    env.JOB_FIT_REPORT_BRIDGE_TOKEN,
  ].filter(Boolean);
  return Boolean(token && validTokens.includes(token));
}

async function handleStateGet(request, env) {
  const authorized = authorizeBridge(request, env);
  if (!authorized) {
    return json({ ok: false, error: "unauthorized" }, 401);
  }

  const namespace = getKvNamespace(env);
  if (!namespace) {
    return json({ ok: false, error: "missing_kv_namespace" }, 500);
  }

  const payload = await request.json();
  const stateKey = sanitizeStateKey(payload.key);
  if (!stateKey) {
    return json({ ok: false, error: "invalid_state_key" }, 400);
  }

  const raw = await namespace.get(`state:${stateKey}`, "text");
  if (raw === null) {
    return json({ ok: true, found: false });
  }

  try {
    return json({ ok: true, found: true, value: JSON.parse(raw) });
  } catch {
    return json({ ok: true, found: true, value: raw });
  }
}

async function handleStatePut(request, env) {
  const authorized = authorizeBridge(request, env);
  if (!authorized) {
    return json({ ok: false, error: "unauthorized" }, 401);
  }

  const namespace = getKvNamespace(env);
  if (!namespace) {
    return json({ ok: false, error: "missing_kv_namespace" }, 500);
  }

  const payload = await request.json();
  const stateKey = sanitizeStateKey(payload.key);
  if (!stateKey) {
    return json({ ok: false, error: "invalid_state_key" }, 400);
  }

  const ttlSeconds = normalizeTtlSeconds(payload.ttl_seconds);
  const options = ttlSeconds ? { expirationTtl: ttlSeconds } : {};
  await namespace.put(`state:${stateKey}`, JSON.stringify(payload.value ?? null), options);
  return json({ ok: true, key: stateKey, ttl_seconds: ttlSeconds || null });
}

async function maybeStoreInboxLog(env, update) {
  const namespace = getKvNamespace(env);
  if (!namespace) {
    return;
  }

  const message = update?.message || update?.edited_message;
  if (!message?.text) {
    return;
  }

  const text = message.text.trim();
  if (!text || text.startsWith("/")) {
    return;
  }

  const timestamp = message.date ? new Date(message.date * 1000) : new Date();
  const date = formatKstDate(timestamp);
  const payload = {
    kind: "inbox",
    date,
    received_at: formatKstIso(timestamp),
    chat_id: String(message.chat?.id || ""),
    username: message.from?.username || "",
    full_name: [message.from?.first_name, message.from?.last_name].filter(Boolean).join(" ").trim(),
    message_id: String(message.message_id || ""),
    text,
  };
  const storageKey = await buildStorageKey("inbox", date, text);
  await namespace.put(storageKey, JSON.stringify(payload), {
    expirationTtl: 60 * 60 * 24 * 14,
  });
}

function getKvNamespace(env) {
  return env.TELEGRAM_MEMORY_KV || null;
}

async function buildStorageKey(kind, date, seed) {
  const safeSeed = sanitizeSeed(seed);
  const hash = await digest(`${kind}:${date}:${safeSeed}:${Date.now()}`);
  return `${kind}:${date}:${hash}`;
}

function sanitizeKind(kind) {
  return kind === "inbox" ? "inbox" : "outbox";
}

function sanitizeDate(date) {
  return /^\d{4}-\d{2}-\d{2}$/.test(date || "") ? date : new Date().toISOString().slice(0, 10);
}

function sanitizeSeed(value) {
  return String(value || "").slice(0, 200);
}

function sanitizeFilename(value) {
  const cleaned = String(value || "")
    .replace(/[^0-9A-Za-z._-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return cleaned || `job-report-${Date.now()}.md`;
}

function sanitizeStateKey(value) {
  const cleaned = String(value || "")
    .replace(/[^0-9A-Za-z._:/-]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  return cleaned.slice(0, 200);
}

function normalizeTtlSeconds(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return 0;
  }
  return Math.min(Math.floor(parsed), 60 * 60 * 24 * 365);
}

function formatKstDate(date) {
  return new Date(date.getTime() + 9 * 60 * 60 * 1000).toISOString().slice(0, 10);
}

function formatKstIso(date) {
  return new Date(date.getTime() + 9 * 60 * 60 * 1000)
    .toISOString()
    .replace("Z", "+09:00");
}

async function digest(value) {
  const data = new TextEncoder().encode(value);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const bytes = Array.from(new Uint8Array(hashBuffer)).slice(0, 8);
  return bytes.map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
