import { NextResponse, type NextRequest } from "next/server";
import { defaultLocale, hasLocale } from "@/i18n/config";

// Russian (default) is served at unprefixed URLs by rewriting to /ru/...; /kk and /en pass through.
// /ru/... redirects to the unprefixed URL so each page has one address.
export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const first = pathname.split("/")[1] ?? "";
  const url = request.nextUrl.clone();

  if (first === defaultLocale) {
    url.pathname = pathname.slice(defaultLocale.length + 1) || "/";
    return NextResponse.redirect(url);
  }
  if (hasLocale(first)) return NextResponse.next();

  url.pathname = `/${defaultLocale}${pathname === "/" ? "" : pathname}`;
  return NextResponse.rewrite(url);
}

export const config = {
  // Skip /api (video uploads must not be buffered by the proxy), Next internals and files.
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
