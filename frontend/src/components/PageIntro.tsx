"use client";

import Link from "next/link";
import { useI18n } from "@/i18n/I18nProvider";

// Title block of the two demo pages. Reads its text on the client so it follows the language
// switcher without a reload.
export function PageIntro({ page }: { page: "inferencePage" | "dashboardPage" }) {
  const { t, href } = useI18n();
  const { label, title, lead } = t[page];
  return (
    <header className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
        <Link href={href("/")} className="hover:text-foreground">
          {t.nav.overview}
        </Link>{" "}
        / {label}
      </p>
      <h1 className="text-[28px] font-bold leading-tight md:text-[32px]">{title}</h1>
      <p className="max-w-2xl text-base font-light text-muted">{lead}</p>
    </header>
  );
}
