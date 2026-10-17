import { BrandMark } from "@/components/BrandMark";
import { Dashboard } from "@/components/Dashboard";

export default function Home() {
  return (
    <>
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex h-16 w-full max-w-5xl items-center justify-between px-4">
          <BrandMark />
          <span className="text-sm font-semibold text-muted">DataThon 2026</span>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-5xl flex-col gap-8 px-4 py-10">
        <section className="bg-hero rounded-3xl px-8 py-12 text-white">
          {/* Text stays on the dark side of the gradient (≤60% width) for contrast. */}
          <div className="max-w-[60%] min-w-64">
            <p className="text-xs font-semibold uppercase tracking-[0.06em] text-white/80">
              ML inference
            </p>
            <h1 className="mt-2 text-4xl font-extrabold leading-tight sm:text-5xl">DataThon 2026</h1>
            <p className="mt-3 text-base font-light text-white/90">
              Next.js → Backend API → ML Inference API
            </p>
          </div>
        </section>

        <Dashboard />
      </main>
    </>
  );
}
