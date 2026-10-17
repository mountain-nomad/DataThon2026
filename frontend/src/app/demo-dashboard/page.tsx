import type { Metadata } from "next";
import { MonitoringDashboard } from "@/components/monitoring/MonitoringDashboard";
import { PageIntro } from "@/components/PageIntro";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = { title: "Monitoring Dashboard · Cash Operations Monitoring" };

export default function DashboardPage() {
  return (
    <>
      <SiteHeader wide />
      <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-4 py-10 pb-24">
        <PageIntro
          label="Monitoring dashboard"
          title="Monitoring Dashboard"
          lead="Explore multi-camera monitoring, detected incidents and operational analytics."
        />
        <MonitoringDashboard />
      </main>
    </>
  );
}
