"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark } from "./BrandMark";

const NAV = [
  { href: "/demo-inference", label: "Inference demo", short: "Inference" },
  { href: "/demo-dashboard", label: "Monitoring dashboard", short: "Dashboard" },
];

export function SiteHeader({ cta, wide = false }: { cta?: { href: string; label: string }; wide?: boolean }) {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface">
      <div className={`mx-auto flex h-16 w-full items-center gap-6 px-4 md:gap-8 ${wide ? "max-w-7xl" : "max-w-6xl"}`}>
        <Link href="/" aria-label="Overview" className="shrink-0 py-2">
          <BrandMark />
        </Link>
        <nav className="flex flex-1 gap-5 text-sm font-semibold text-muted md:gap-6">
          {NAV.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={active ? "text-foreground" : "hover:text-foreground"}
              >
                <span className="md:hidden">{item.short}</span>
                <span className="hidden md:inline">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        {cta && (
          <Link
            href={cta.href}
            className="hidden shrink-0 rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-hover sm:inline-flex"
          >
            {cta.label}
          </Link>
        )}
      </div>
    </header>
  );
}
