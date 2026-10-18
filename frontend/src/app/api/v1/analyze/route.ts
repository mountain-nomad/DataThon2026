import type { NextRequest } from "next/server";
import { authEnabled, validSession, validApiKey, SESSION_COOKIE } from "@/lib/site-auth";

// Upload proxy for /demo-inference (backend_description.md §8). The backend's /api/v1 needs
// X-API-Key, which must never reach the browser, so this server-side handler adds it.
// It's a static route on purpose: the /api/:path* rewrite in next.config.ts runs before
// dynamic routes, but after static ones. Everything else under /api still goes through it.

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(request: NextRequest) {
  const suppliedKey = request.headers.get("x-api-key");
  if (suppliedKey !== null) {
    if (!validApiKey(suppliedKey)) {
      return Response.json({ detail: "Invalid or missing API key" }, { status: 401 });
    }
  } else if (authEnabled() && !validSession(request.cookies.get(SESSION_COOKIE)?.value)) {
    return Response.json({ detail: "Invalid or missing API key" }, { status: 401 });
  }
  const apiKey = suppliedKey ?? process.env.ANALYSIS_API_KEY;
  if (!apiKey) {
    return Response.json({ detail: "ANALYSIS_API_KEY is not set on the frontend server." }, { status: 500 });
  }
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}/api/v1/analyze`, {
      method: "POST",
      headers: { "content-type": request.headers.get("content-type") ?? "", "x-api-key": apiKey },
      // Stream the video through instead of buffering it.
      body: request.body,
      duplex: "half",
    } as RequestInit & { duplex: "half" });
  } catch {
    return Response.json({ detail: "The analysis backend isn't reachable." }, { status: 503 });
  }
  return new Response(res.body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}
