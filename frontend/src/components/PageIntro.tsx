import Link from "next/link";

// Title block of the two demo pages.
export function PageIntro({ label, title, lead }: { label: string; title: string; lead: string }) {
  return (
    <header className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
        <Link href="/" className="hover:text-foreground">
          Overview
        </Link>{" "}
        / {label}
      </p>
      <h1 className="text-[28px] font-bold leading-tight md:text-[32px]">{title}</h1>
      <p className="max-w-2xl text-base font-light text-muted">{lead}</p>
    </header>
  );
}
