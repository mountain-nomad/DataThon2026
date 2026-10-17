import Link from "next/link";
import { BrandMark } from "./BrandMark";

type NavItem = { href: string; label: string };

export function SiteHeader({ nav = [], cta }: { nav?: NavItem[]; cta: NavItem }) {
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-surface">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-8 px-4">
        <Link href="/" aria-label="Forte — home" className="py-2">
          <BrandMark />
        </Link>
        <nav className="hidden flex-1 gap-6 text-sm font-semibold text-muted md:flex">
          {nav.map((item) => (
            <a key={item.href} href={item.href} className="hover:text-foreground">
              {item.label}
            </a>
          ))}
        </nav>
        <Link
          href={cta.href}
          className="ml-auto rounded-full bg-primary px-5 py-2 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-hover"
        >
          {cta.label}
        </Link>
      </div>
    </header>
  );
}
