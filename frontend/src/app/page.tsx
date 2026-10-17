import Link from "next/link";
import { BrandMark } from "@/components/BrandMark";
import { buttonPrimaryLinkClass, buttonSecondaryClass } from "@/components/Card";
import { LiveModelCard } from "@/components/landing/LiveModelCard";
import { ModelFacts } from "@/components/landing/ModelFacts";
import { TryExample } from "@/components/landing/TryExample";
import { ModelProvider } from "@/components/landing/useModel";
import { SiteHeader } from "@/components/SiteHeader";

const NAV = [
  { href: "#how", label: "How it works" },
  { href: "#model", label: "The model" },
  { href: "#try", label: "Try it" },
];

const STEPS = [
  {
    title: "Send a record or a file",
    body: "One JSON record, or a CSV with a header row of feature names. Missing values are fine; they reach the model as nulls.",
  },
  {
    title: "The model answers",
    body: "A gradient-boosted baseline trained on the competition data. Classification returns the class and its probability; regression returns a number.",
  },
  {
    title: "Every call is kept",
    body: "Input, output and model version are stored with each request, so any result can be traced back to the exact model that produced it.",
  },
];

// Numbered section headings follow the brand page's own "01 · Logotype color" pattern.
function SectionHeading({ n, label, title, lead }: { n: string; label: string; title: string; lead?: string }) {
  return (
    <div className="flex max-w-2xl flex-col gap-3">
      <p className="flex items-baseline gap-3 text-xs font-semibold uppercase tracking-[0.06em] text-muted">
        <span className="text-primary tabular-nums">{n}</span>
        {label}
      </p>
      <h2 className="text-[28px] font-bold leading-tight md:text-[32px]">{title}</h2>
      {lead && <p className="text-base text-muted">{lead}</p>}
    </div>
  );
}

export default function Home() {
  return (
    <ModelProvider>
      <SiteHeader nav={NAV} cta={{ href: "/dashboard", label: "Open dashboard" }} />

      <main className="mx-auto flex w-full max-w-6xl flex-col gap-24 px-4 pt-8 pb-24 md:gap-32">
        {/* Hero: white, type-led. The logo and one magenta button carry the brand. */}
        <section className="grid gap-12 pt-8 md:pt-16 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] lg:items-end">
          <div className="flex flex-col gap-6">
            <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">
              DataThon 2026 · Prototype
            </p>
            <h1 className="text-[40px] font-extrabold leading-[1.05] tracking-tight md:text-5xl">
              From a row of data to an answer you can trace.
            </h1>
            <p className="max-w-md text-lg font-light text-muted">
              Send a record, get the model&apos;s prediction with its confidence, and keep a log of
              every call.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <a href="#try" className={buttonPrimaryLinkClass}>
                Try a prediction
              </a>
              <a href="#how" className={buttonSecondaryClass}>
                How it works
              </a>
            </div>
          </div>
          <div className="flex lg:justify-end">
            <LiveModelCard />
          </div>
        </section>

        <section id="how" className="flex scroll-mt-24 flex-col gap-12">
          <SectionHeading n="01" label="How it works" title="Three steps, no setup on your side." />
          <div>
            {/* Primary gradient as a thin rule that rises left to right across the steps. */}
            <div aria-hidden className="bg-gradient-primary h-1 rounded-full" />
            <ol className="grid gap-10 pt-8 md:grid-cols-3 md:gap-12">
              {STEPS.map((step) => (
                <li key={step.title} className="flex flex-col gap-2">
                  <h3 className="text-xl font-bold">{step.title}</h3>
                  <p className="text-[15px] leading-relaxed text-muted">{step.body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section id="model" className="grid scroll-mt-24 gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
          <SectionHeading
            n="02"
            label="The model"
            title="What's running right now."
            lead="Read live from the inference service. Metrics come from a holdout split at training time."
          />
          <ModelFacts />
        </section>

        <section id="try" className="flex scroll-mt-24 flex-col gap-10">
          <SectionHeading
            n="03"
            label="Try it"
            title="Send a real record."
            lead="This is the same request the dashboard makes. Running it adds one entry to the prediction log."
          />
          <TryExample />
        </section>

        <section className="flex flex-col gap-6 border-t border-border pt-12 md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col gap-2">
            <h2 className="text-[28px] font-bold leading-tight md:text-[32px]">Ready for the real dataset?</h2>
            <p className="text-base text-muted">
              Batch uploads, the request history and service status live in the dashboard.
            </p>
          </div>
          <Link href="/dashboard" className={`${buttonPrimaryLinkClass} self-start md:self-auto`}>
            Open the dashboard
          </Link>
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
            {NAV.map((item) => (
              <a key={item.href} href={item.href} className="hover:text-foreground">
                {item.label}
              </a>
            ))}
            <Link href="/dashboard" className="hover:text-foreground">
              Dashboard
            </Link>
          </nav>
        </div>
      </footer>
    </ModelProvider>
  );
}
