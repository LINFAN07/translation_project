/**
 * Gemini HTTP 代理：Google API Key 只存在 Worker Secrets (GEMINI_API_KEY)。
 * 可選 WORKER_AUTH_SECRET：請求須帶 Authorization: Bearer <secret>
 */
export interface Env {
  GEMINI_API_KEY: string;
  WORKER_AUTH_SECRET?: string;
}

const JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
};

function corsHeaders(request: Request): Record<string, string> {
  const origin = request.headers.get("Origin");
  const h: Record<string, string> = {
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Max-Age": "86400",
  };
  if (origin) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Vary"] = "Origin";
  } else {
    h["Access-Control-Allow-Origin"] = "*";
  }
  return h;
}

function json(
  data: unknown,
  status = 200,
  request: Request
): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...JSON_HEADERS, ...corsHeaders(request) },
  });
}

function unauthorized(request: Request): Response {
  return json({ ok: false, error: "Unauthorized" }, 401, request);
}

function checkAuth(request: Request, env: Env): Response | null {
  const need = (env.WORKER_AUTH_SECRET || "").trim();
  if (!need) {
    return null;
  }
  const auth = request.headers.get("Authorization") || "";
  const expected = `Bearer ${need}`;
  if (auth !== expected) {
    return unauthorized(request);
  }
  return null;
}

function extractGenerateText(body: unknown): string | null {
  if (!body || typeof body !== "object") {
    return null;
  }
  const o = body as Record<string, unknown>;
  const candidates = o.candidates;
  if (!Array.isArray(candidates) || candidates.length === 0) {
    return null;
  }
  const c0 = candidates[0] as Record<string, unknown>;
  const content = c0.content as Record<string, unknown> | undefined;
  if (!content) {
    return null;
  }
  const parts = content.parts;
  if (!Array.isArray(parts)) {
    return null;
  }
  let out = "";
  for (const p of parts) {
    if (p && typeof p === "object" && "text" in p) {
      const t = (p as { text?: string }).text;
      if (typeof t === "string") {
        out += t;
      }
    }
  }
  const s = out.trim();
  return s || null;
}

async function geminiGenerate(
  env: Env,
  model: string,
  prompt: string
): Promise<{ ok: true; text: string } | { ok: false; error: string; status: number }> {
  const key = (env.GEMINI_API_KEY || "").trim();
  if (!key) {
    return { ok: false, error: "Server misconfigured: missing GEMINI_API_KEY", status: 500 };
  }
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
    model
  )}:generateContent`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": key,
    },
    body: JSON.stringify({
      contents: [{ role: "user", parts: [{ text: prompt }] }],
    }),
  });
  const text = await res.text();
  let body: unknown;
  try {
    body = JSON.parse(text);
  } catch {
    return {
      ok: false,
      error: `Gemini HTTP ${res.status}: ${text.slice(0, 500)}`,
      status: res.status >= 400 ? res.status : 502,
    };
  }
  if (!res.ok) {
    const errMsg =
      typeof body === "object" && body !== null && "error" in body
        ? JSON.stringify((body as { error: unknown }).error)
        : text.slice(0, 500);
    return { ok: false, error: errMsg, status: res.status };
  }
  const extracted = extractGenerateText(body);
  if (!extracted) {
    return {
      ok: false,
      error: "Empty or blocked model response",
      status: 502,
    };
  }
  return { ok: true, text: extracted };
}

async function geminiCountTokens(
  env: Env,
  model: string,
  text: string
): Promise<{ ok: true; totalTokens: number } | { ok: false; error: string; status: number }> {
  const key = (env.GEMINI_API_KEY || "").trim();
  if (!key) {
    return { ok: false, error: "Server misconfigured: missing GEMINI_API_KEY", status: 500 };
  }
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(
    model
  )}:countTokens`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-goog-api-key": key,
    },
    body: JSON.stringify({
      contents: [{ parts: [{ text }] }],
    }),
  });
  const raw = await res.text();
  let body: unknown;
  try {
    body = JSON.parse(raw);
  } catch {
    return {
      ok: false,
      error: `Gemini HTTP ${res.status}: ${raw.slice(0, 500)}`,
      status: res.status >= 400 ? res.status : 502,
    };
  }
  if (!res.ok) {
    const errMsg =
      typeof body === "object" && body !== null && "error" in body
        ? JSON.stringify((body as { error: unknown }).error)
        : raw.slice(0, 500);
    return { ok: false, error: errMsg, status: res.status };
  }
  if (
    typeof body === "object" &&
    body !== null &&
    "totalTokens" in body &&
    typeof (body as { totalTokens: unknown }).totalTokens === "number"
  ) {
    return { ok: true, totalTokens: (body as { totalTokens: number }).totalTokens };
  }
  return { ok: false, error: "Invalid countTokens response", status: 502 };
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(request) });
    }

    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/") {
      return json(
        {
          ok: true,
          service: "translation-gemini-proxy",
          endpoints: ["POST /generate", "POST /count-tokens"],
        },
        200,
        request
      );
    }

    if (request.method !== "POST") {
      return json({ ok: false, error: "Method not allowed" }, 405, request);
    }

    const authErr = checkAuth(request, env);
    if (authErr) {
      return authErr;
    }

    try {
      const payload = (await request.json()) as Record<string, unknown>;
      const model = String(payload.model || "gemini-2.5-flash").trim();

      if (url.pathname === "/generate" || url.pathname.endsWith("/generate")) {
        const prompt = String(payload.prompt ?? "");
        if (!prompt) {
          return json({ ok: false, error: "Missing prompt" }, 400, request);
        }
        const result = await geminiGenerate(env, model, prompt);
        if (!result.ok) {
          return json({ ok: false, error: result.error }, result.status, request);
        }
        return json({ ok: true, text: result.text }, 200, request);
      }

      if (
        url.pathname === "/count-tokens" ||
        url.pathname.endsWith("/count-tokens")
      ) {
        const text = String(payload.text ?? "");
        if (!text) {
          return json({ ok: false, error: "Missing text" }, 400, request);
        }
        const result = await geminiCountTokens(env, model, text);
        if (!result.ok) {
          return json({ ok: false, error: result.error }, result.status, request);
        }
        return json(
          { ok: true, totalTokens: result.totalTokens },
          200,
          request
        );
      }

      return json({ ok: false, error: "Not found" }, 404, request);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      return json({ ok: false, error: msg }, 500, request);
    }
  },
};
