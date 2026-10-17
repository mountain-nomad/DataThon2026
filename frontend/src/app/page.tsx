import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { buttonPrimaryLinkClass, buttonSecondaryClass } from "@/components/Card";
import { MediaPlaceholder } from "@/components/media/MediaPlaceholder";
import { SiteHeader } from "@/components/SiteHeader";

const VALUE = [
  {
    title: "Spots suspicious actions",
    body: "Local models watch the cash-desk footage and flag actions that may break cash-handling discipline.",
  },
  {
    title: "Pinpoints the moment",
    body: "Each detection comes with the exact timecode in the original recording, so nobody scrubs through hours of video.",
  },
  {
    title: "Hands evidence to a person",
    body: "Evidence frames, a description and the referenced rule go to a reviewer. The model flags; a person decides.",
  },
];

const DEMOS = [
  {
    href: "/demo-inference",
    title: "Video Inference Demo",
    body: "Upload a CCTV recording and analyze it for potential compliance violations.",
    action: "Open Inference Demo",
    media: "Inference demo preview",
  },
  {
    href: "/demo-dashboard",
    title: "Monitoring Dashboard Demo",
    body: "Explore multi-camera monitoring, detected incidents and operational analytics.",
    action: "Open Monitoring Dashboard",
    media: "Dashboard demo preview",
  },
];

const PRINCIPLES = [
  { title: "Runs locally", body: "Video and inference stay on local machines. No cloud AI APIs or external video services." },
  { title: "No face recognition", body: "The system looks at actions around cash, never at who a person is." },
  { title: "AI flags, people confirm", body: "Every detection is a potential violation until a person reviews it." },
];

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

export default function Home() {
  return (
    <>
      <SiteHeader cta={{ href: "/demo-inference", label: "Analyze a video" }} />

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-24 px-4 pt-8 pb-24 md:gap-32">
        <section className="grid gap-12 pt-8 md:pt-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-center">
          <div className="flex flex-col gap-6">
            <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
              DataThon 2026 · Prototype
            </p>
            <h1 className="text-[40px] font-extrabold leading-[1.05] tracking-tight md:text-5xl">
              Cash Operations Monitoring
            </h1>
            <p className="max-w-md text-lg font-light text-muted">
              AI-powered video monitoring for cash operations: it finds suspicious actions, pins them
              to the exact moment and gives a person the evidence to check.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link href="/demo-inference" className={buttonPrimaryLinkClass}>
                Open Inference Demo
              </Link>
              <Link href="/demo-dashboard" className={buttonSecondaryClass}>
                Open Monitoring Dashboard
              </Link>
            </div>
          </div>
          <MediaPlaceholder label="Hero visual" hint="Image or video placeholder, 16:9" />
        </section>

        <section className="flex flex-col gap-12">
          <SectionHeading n="01" label="What it does" title="From hours of footage to a few moments worth checking." />
          <div>
            {/* Primary gradient as a thin rule that rises left to right across the steps. */}
            <div aria-hidden className="bg-gradient-primary h-1 rounded-full" />
            <ol className="grid gap-10 pt-8 md:grid-cols-3 md:gap-12">
              {VALUE.map((item) => (
                <li key={item.title} className="flex flex-col gap-2">
                  <h3 className="text-xl font-bold">{item.title}</h3>
                  <p className="text-[15px] leading-relaxed text-muted">{item.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="demos" className="flex scroll-mt-24 flex-col gap-12">
          <SectionHeading n="02" label="Demos" title="Pick a scenario." />
          <div className="grid gap-6 md:grid-cols-2">
            {DEMOS.map((demo) => (
              <article key={demo.href} className="flex flex-col gap-5 rounded-2xl border border-border p-4 md:p-6">
                <MediaPlaceholder label={demo.media} hint="Screenshot placeholder" />
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
          <SectionHeading n="03" label="Ground rules" title="Built to support a reviewer, not replace one." />
          <dl className="grid gap-10 border-t border-border pt-8 md:grid-cols-3 md:gap-12">
            {PRINCIPLES.map((p) => (
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
              Prototype built for DataThon 2026. Not an official ForteBank product or service.
            </p>
          </div>
          <nav className="flex flex-wrap gap-x-8 gap-y-3 text-sm font-semibold text-muted">
            <Link href="/demo-inference" className="hover:text-foreground">
              Inference demo
            </Link>
            <Link href="/demo-dashboard" className="hover:text-foreground">
              Monitoring dashboard
            </Link>
          </nav>
        </div>
      </footer>
    </>
  );
}
