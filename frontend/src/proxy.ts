import { NextResponse, type NextRequest } from "next/server";
import { defaultLocale, hasLocale } from "@/i18n/config";
import { authEnabled, validSession, validApiKey, SESSION_COOKIE } from "@/lib/site-auth";

const escapeHtml = (s: string) => s.replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  // Jury API authenticates independently of browser sessions.
  if (pathname.startsWith("/api/v1/")) {
    if (!validApiKey(request.headers.get("x-api-key"))) {
      return NextResponse.json({ detail: "Invalid or missing API key" }, { status: 401 });
    }
    return NextResponse.next();
  }
  if (pathname === "/api/auth/login") return NextResponse.next();
  if (authEnabled() && !validSession(request.cookies.get(SESSION_COOKIE)?.value)) {
    if (pathname.startsWith("/api/")) return NextResponse.json({ detail: "Sign in required" }, { status: 401 });
    return new NextResponse(`<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Вход — DataThon</title>
      <style>body{font:16px system-ui;background:#f7f4f6;color:#252025;display:grid;place-items:center;min-height:100vh;margin:0}form{background:white;padding:32px;border-radius:16px;width:min(320px,80vw);box-shadow:0 8px 40px #32112315}label{display:block;margin:16px 0}input,button{box-sizing:border-box;width:100%;padding:12px;margin-top:6px;border:1px solid #bbb;border-radius:8px;font:inherit}button{background:#7a1745;color:white;border:0;cursor:pointer}</style>
      <form action="/api/auth/login" method="post"><h1>Вход в DataThon</h1><label>Логин<input name="username" autocomplete="username" required></label><label>Пароль<input name="password" type="password" autocomplete="current-password" required></label><input type="hidden" name="next" value="${escapeHtml(pathname + search)}"><button>Войти</button></form></html>`,
      { headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "content-security-policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" } });
  }
  if (pathname.startsWith("/api/") || /\.[^/]+$/.test(pathname)) return NextResponse.next();
  const first = pathname.split("/")[1] ?? "";
  if (hasLocale(first)) return NextResponse.next();
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  const protocol = request.headers.get("x-forwarded-proto") ?? "http";
  const target = new URL(`${protocol}://${host ?? request.nextUrl.host}`);
  target.pathname = `/${defaultLocale}${pathname === "/" ? "" : pathname}`;
  target.search = search;
  return NextResponse.redirect(target);
}
export const config = { matcher: ["/((?!_next/static|_next/image|api/v1/analyze).*)"] };
