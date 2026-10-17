import type { Metadata } from "next";
import { MonitoringDashboard } from "@/components/monitoring/MonitoringDashboard";
import { PageIntro } from "@/components/PageIntro";
import { SiteHeader } from "@/components/SiteHeader";
import { getDictionary } from "@/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getDictionary()).meta.dashboardTitle };
}

export default async function DashboardPage() {
  const t = await getDictionary();
  return (
    <>
      <SiteHeader path="/demo-dashboard" wide />
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-10 pb-24">
        <PageIntro label={t.dashboardPage.label} title={t.dashboardPage.title} lead={t.dashboardPage.lead} />
        <MonitoringDashboard />
      </main>
    </>
  );
}
