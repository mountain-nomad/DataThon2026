"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { localePath, type Locale } from "./config";
import { en } from "./dictionaries/en";
import { kk } from "./dictionaries/kk";
import { ru, type Dictionary } from "./dictionaries/ru";

// All three dictionaries ship to the client, so switching language only re-renders the text:
// no navigation, and page state (an uploaded video, analysis results, review marks) survives.
const dictionaries: Record<Locale, Dictionary> = { ru, kk, en };

type I18nValue = {
  locale: Locale;
  t: Dictionary;
  setLocale: (locale: Locale, path: string) => void;
};

const I18nContext = createContext<I18nValue | null>(null);

// Tab title per route; mirrors each page's generateMetadata.
function pageTitle(t: Dictionary, path: string): string {
  if (path === "/demo-inference") return t.meta.inferenceTitle;
  if (path === "/demo-dashboard") return t.meta.dashboardTitle;
  return t.meta.title;
}

// `locale` is the [lang] segment the page was rendered for. The layout keys this provider by it,
// so a real navigation to another locale starts fresh.
export function I18nProvider({ locale: initial, children }: { locale: Locale; children: React.ReactNode }) {
  const [locale, setLocaleState] = useState(initial);

  // The router can restore a cached tree whose layout rendered another <html lang> (e.g. Back to
  // a page that was translated in place), so the provider's own locale wins after every render.
  useEffect(() => {
    document.documentElement.lang = locale;
  });

  // Translate in place: swap the dictionary, then make the URL, <html lang> and the tab title
  // match, so a reload or a shared link opens the same language. replaceState is integrated
  // with the Next router and doesn't reload the page.
  const setLocale = (next: Locale, path: string) => {
    if (next === locale) return;
    setLocaleState(next);
    document.documentElement.lang = next;
    document.title = pageTitle(dictionaries[next], path);
    window.history.replaceState(null, "", localePath(next, path) + window.location.search + window.location.hash);
  };

  return <I18nContext value={{ locale, t: dictionaries[locale], setLocale }}>{children}</I18nContext>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return { ...ctx, href: (path: string) => localePath(ctx.locale, path) };
}
