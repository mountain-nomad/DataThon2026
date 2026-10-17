"use client";

import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { buttonPrimaryLinkClass, buttonSecondaryClass } from "@/components/Card";
import { MediaPlaceholder } from "@/components/media/MediaPlaceholder";
import { SiteHeader } from "@/components/SiteHeader";
import { useI18n } from "@/i18n/I18nProvider";

// Numbered section headings follow the brand page's own "01 · Logotype color" pattern.
function SectionHeading({ n, label, title }: { n: string; label: string; title: string }) {
  return (
    <div className="flex max-w-2xl flex-col gap-3">
      <p className="flex items-baseline gap-3 text-xs font-semibold uppercase tracking-[0.06em] text-muted">
        <span className="text-primary tabular-nums">{n}</span>
        {label}
      </p>
      <h2 className="text-[28px] font-bold leading-tight md:text-[32px]">{title}</h2>
    </div>
  );
}

// Landing content (route "/"). A client component so the language switcher translates it in place.
export function Landing() {
  const { t: dict, href } = useI18n();
  const t = dict.landing;
  const demos = [
    { href: href("/demo-inference"), ...t.demoInference },
    { href: href("/demo-dashboard"), ...t.demoDashboard },
  ];

  return (
    <>
      <SiteHeader path="/" cta />

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-24 px-4 pt-8 pb-24 md:gap-32">
        <section className="grid gap-12 pt-8 md:pt-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-center">
          <div className="flex flex-col gap-6">
            <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
              {t.label}
            </p>
            <h1 className="text-[40px] font-extrabold leading-[1.05] tracking-tight md:text-5xl">
              {t.title}
            </h1>
            <p className="max-w-md text-lg font-light text-muted">
              {t.lead}
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link href={href("/demo-inference")} className={buttonPrimaryLinkClass}>
                {t.openInference}
              </Link>
              <Link href={href("/demo-dashboard")} className={buttonSecondaryClass}>
                {t.openDashboard}
              </Link>
            </div>
          </div>
          <MediaPlaceholder label={t.heroMedia} hint={t.heroMediaHint} />
        </section>

        <section className="flex flex-col gap-12">
          <SectionHeading n="01" label={t.whatLabel} title={t.whatTitle} />
          <div>
            {/* Primary gradient as a thin rule that rises left to right across the steps. */}
            <div aria-hidden className="bg-gradient-primary h-1 rounded-full" />
            <ol className="grid gap-10 pt-8 md:grid-cols-3 md:gap-12">
              {t.value.map((item) => (
                <li key={item.title} className="flex flex-col gap-2">
                  <h3 className="text-xl font-bold">{item.title}</h3>
                  <p className="text-[15px] leading-relaxed text-muted">{item.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="demos" className="flex scroll-mt-24 flex-col gap-12">
          <SectionHeading n="02" label={t.demosLabel} title={t.demosTitle} />
          <div className="grid gap-6 md:grid-cols-2">
            {demos.map((demo) => (
              <article key={demo.href} className="flex flex-col gap-5 rounded-2xl border border-border p-4 md:p-6">
                <MediaPlaceholder label={demo.media} hint={t.screenshotHint} />
                <div className="flex flex-col gap-2">
                  <h3 className="text-xl font-bold">{demo.title}</h3>
                  <p className="text-[15px] leading-relaxed text-muted">{demo.body}</p>
                </div>
                <Link href={demo.href} className={`${buttonPrimaryLinkClass} mt-auto self-start`}>
                  {demo.action}
                </Link>
              </article>
            ))}
          </div>
        </section>

        <section className="flex flex-col gap-12">
          <SectionHeading n="03" label={t.rulesLabel} title={t.rulesTitle} />
          <dl className="grid gap-10 border-t border-border pt-8 md:grid-cols-3 md:gap-12">
            {t.principles.map((p) => (
              <div key={p.title} className="flex flex-col gap-2">
                <dt className="text-xl font-bold">{p.title}</dt>
                <dd className="text-[15px] leading-relaxed text-muted">{p.body}</dd>
              </div>
            ))}
          </dl>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-12 md:flex-row md:items-start md:justify-between">
          <div className="flex max-w-sm flex-col gap-4">
            <BrandMark height={20} />
            <p className="text-sm text-muted">
              {t.footerNote}
            </p>
          </div>
          <nav className="flex flex-wrap gap-x-8 gap-y-3 text-sm font-semibold text-muted">
            <Link href={href("/demo-inference")} className="hover:text-foreground">
              {dict.nav.inference}
            </Link>
            <Link href={href("/demo-dashboard")} className="hover:text-foreground">
              {dict.nav.dashboard}
            </Link>
          </nav>
        </div>
      </footer>
    </>
  );
}
