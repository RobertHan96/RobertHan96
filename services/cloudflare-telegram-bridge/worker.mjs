export default {
  async fetch(request, env) {
    if (request.method === "GET") {
      return json({ ok: true, status: "healthy" });
    }

    if (request.method !== "POST") {
      return json({ ok: false, error: "method_not_allowed" }, 405);
    }

    const secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
    if (!secret || secret !== env.TELEGRAM_WEBHOOK_SECRET_TOKEN) {
      return json({ ok: false, error: "invalid_secret" }, 401);
    }

    const update = await request.json();

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

function json(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json; charset=utf-8" },
  });
}
