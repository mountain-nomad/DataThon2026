import type { Metadata } from "next";
import { Dashboard } from "@/components/Dashboard";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = { title: "Dashboard · DataThon 2026" };

export default function DashboardPage() {
  return (
    <>
      <SiteHeader cta={{ href: "/", label: "Overview" }} />
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-10">
        <header className="flex flex-col gap-1">
          <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">Workspace</p>
          <h1 className="text-[28px] font-bold leading-tight md:text-[32px]">Dashboard</h1>
        </header>
        <Dashboard />
      </main>
    </>
  );
}
