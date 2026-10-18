import { createHmac, timingSafeEqual } from "node:crypto";

export const SESSION_COOKIE = "datathon_session";
export const SESSION_SECONDS = 12 * 60 * 60;
export function authEnabled() { return Boolean(process.env.SITE_LOGIN_PASSWORD); }
function signature(value: string) {
  const secret = process.env.SITE_SESSION_SECRET;
  if (!secret) throw new Error("SITE_SESSION_SECRET is required");
  return createHmac("sha256", secret).update(value).digest("base64url");
}
function constantTimeEqual(a: string, b: string) {
  const x = createHmac("sha256", "credential-comparison").update(a).digest();
  const y = createHmac("sha256", "credential-comparison").update(b).digest();
  return timingSafeEqual(x, y);
}
export function validApiKey(key: string | null) {
  const expected = process.env.ANALYSIS_API_KEY;
  return Boolean(key && expected) && constantTimeEqual(key!, expected!);
}
export function credentialsValid(user: string, password: string) {
  const expectedUser = process.env.SITE_LOGIN_USER ?? "datathon";
  const expectedPassword = process.env.SITE_LOGIN_PASSWORD ?? "";
  return Boolean(expectedPassword) && constantTimeEqual(user, expectedUser) && constantTimeEqual(password, expectedPassword);
}
export function createSession() {
  const value = String(Math.floor(Date.now() / 1000) + SESSION_SECONDS);
  return `${value}.${signature(value)}`;
}
export function validSession(token?: string) {
  if (!token) return false;
  const [expires, supplied, extra] = token.split(".");
  if (extra || !expires || !supplied || !/^\d+$/.test(expires)) return false;
  const expiry = Number(expires), now = Math.floor(Date.now() / 1000);
  if (expiry <= now || expiry > now + SESSION_SECONDS) return false;
  const expected = Buffer.from(signature(expires)), actual = Buffer.from(supplied);
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}
export function safeReturnPath(value: string) {
  return value.startsWith("/") && !value.startsWith("//") && !/[\\\r\n]/.test(value)
    ? value : "/ru/demo-inference";
}
