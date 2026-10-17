export function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-border bg-surface p-6 flex flex-col gap-4">
      <h2 className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{title}</h2>
      {children}
    </section>
  );
}

export function ErrorText({ error }: { error: string | null }) {
  return error ? (
    <p role="alert" className="rounded-xl bg-danger-bg px-3 py-2 text-sm text-danger-fg">
      <span className="font-semibold">Error: </span>
      {error}
    </p>
  ) : null;
}

const focusRing =
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface";

export const buttonClass = `self-start rounded-full bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary-hover disabled:opacity-50 disabled:hover:bg-primary ${focusRing}`;

const pill = "inline-flex items-center justify-center rounded-full px-6 py-2.5 text-sm font-semibold transition-colors";

export const buttonSecondaryClass = `${pill} border border-border text-foreground hover:bg-surface-muted ${focusRing}`;

export const buttonPrimaryLinkClass = `${pill} bg-primary text-primary-foreground hover:bg-primary-hover ${focusRing}`;

export const inputClass = `rounded-xl border border-border bg-surface-muted/60 p-3 text-sm ${focusRing}`;

export function StatusDot({ ok }: { ok: boolean | null }) {
  const color = ok === null ? "bg-border" : ok ? "bg-forte-sky" : "bg-forte-coral";
  return <span aria-hidden className={`inline-block size-2.5 rounded-full ${color}`} />;
}
