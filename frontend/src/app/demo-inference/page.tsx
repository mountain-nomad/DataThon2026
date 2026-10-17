import type { Metadata } from "next";
import { InferenceDemo } from "@/components/inference/InferenceDemo";
import { PageIntro } from "@/components/PageIntro";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = { title: "Video Inference · Cash Operations Monitoring" };

export default function InferencePage() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-10 pb-24">
        <PageIntro
          label="Inference demo"
          title="Video Inference"
          lead="Upload a CCTV recording and analyze it for potential compliance violations."
        />
        <InferenceDemo />
      </main>
    </>
  );
}
