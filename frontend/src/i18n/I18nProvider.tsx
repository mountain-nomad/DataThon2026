"use client";

import { createContext, useContext } from "react";
import { localePath, type Locale } from "./config";
import type { Dictionary } from "./dictionaries/ru";

const I18nContext = createContext<{ locale: Locale; t: Dictionary } | null>(null);

// The root layout loads the dictionary on the server and hands it to client components here.
export function I18nProvider({ locale, dict, children }: { locale: Locale; dict: Dictionary; children: React.ReactNode }) {
  return <I18nContext value={{ locale, t: dict }}>{children}</I18nContext>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return { ...ctx, href: (path: string) => localePath(ctx.locale, path) };
}
