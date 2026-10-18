import { NextRequest, NextResponse } from "next/server";
import { authEnabled, credentialsValid, createSession, safeReturnPath, SESSION_COOKIE, SESSION_SECONDS } from "@/lib/site-auth";

export async function POST(request: NextRequest) {
  if (!authEnabled()) return new Response("Login is not configured", { status: 503 });
  const origin = request.headers.get("origin");
  const host = request.headers.get("x-forwarded-host") ?? request.headers.get("host");
  if (origin && new URL(origin).host !== host) return new Response("Invalid origin", { status: 403 });
  const form = await request.formData();
  if (!credentialsValid(String(form.get("username") ?? ""), String(form.get("password") ?? ""))) {
    return new Response("Неверный логин или пароль. Вернитесь назад и повторите вход.",
      { status: 401, headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" } });
  }
  const response = new NextResponse(null, { status: 303, headers: {
    location: safeReturnPath(String(form.get("next") ?? "/ru/demo-inference")), "cache-control": "no-store"
  } });
  response.cookies.set(SESSION_COOKIE, createSession(), {
    httpOnly: true, sameSite: "lax", path: "/", maxAge: SESSION_SECONDS,
    secure: (request.headers.get("x-forwarded-proto") ?? request.nextUrl.protocol.replace(":", "")) === "https"
  });
  return response;
}
