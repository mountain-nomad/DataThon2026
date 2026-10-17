"use client";

import Link from "next/link";
import { useI18n } from "@/i18n/I18nProvider";
import { BrandMark } from "./BrandMark";
import { LanguageSwitcher } from "./LanguageSwitcher";

// `path` is the current route without the locale prefix. Pages pass it explicitly instead of
// reading usePathname(), which would mismatch on hydration behind the proxy's /ru rewrite.
export function SiteHeader({ path, cta, wide = false }: { path: string; cta?: boolean; wide?: boolean }) {
  const { t, href } = useI18n();
  const nav = [
    { path: "/demo-inference", label: t.nav.inference, short: t.nav.inferenceShort },
    { path: "/demo-dashboard", label: t.nav.dashboard, short: t.nav.dashboardShort },
  ];
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface">
      <div className={`mx-auto flex h-16 w-full items-center gap-4 px-4 md:gap-8 ${wide ? "max-w-7xl" : "max-w-6xl"}`}>
        <Link href={href("/")} aria-label={t.nav.home} className="shrink-0 py-2">
          <BrandMark />
        </Link>
        <nav className="flex min-w-0 flex-1 gap-4 text-sm font-semibold text-muted md:gap-6">
          {nav.map((item) => {
            const active = path === item.path;
            return (
              <Link
                key={item.path}
                href={href(item.path)}
                aria-current={active ? "page" : undefined}
                className={active ? "text-foreground" : "hover:text-foreground"}
              >
                <span className="md:hidden">{item.short}</span>
                <span className="hidden md:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        <LanguageSwitcher path={path} />
        {cta && (
          <Link
            href={href("/demo-inference")}
            className="hidden shrink-0 rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-hover lg:inline-flex"
          >
            {t.landing.cta}
          </Link>
        )}
      </div>
    </header>
  );
}
