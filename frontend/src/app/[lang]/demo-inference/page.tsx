import type { Metadata } from "next";
import { InferenceDemo } from "@/components/inference/InferenceDemo";
import { PageIntro } from "@/components/PageIntro";
import { SiteHeader } from "@/components/SiteHeader";
import { getDictionary } from "@/i18n/dictionaries";

export async function generateMetadata(): Promise<Metadata> {
  return { title: (await getDictionary()).meta.inferenceTitle };
}

export default function InferencePage() {
  return (
    <>
      <SiteHeader path="/demo-inference" />
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-10 px-4 py-10 pb-24">
        <PageIntro page="inferencePage" />
        <InferenceDemo />
      </main>
    </>
  );
}
