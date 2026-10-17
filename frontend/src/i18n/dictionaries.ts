import { lang } from "next/root-params";
import { notFound } from "next/navigation";
import { hasLocale, type Locale } from "./config";

const dictionaries = {
  ru: () => import("./dictionaries/ru").then((m) => m.ru),
  kk: () => import("./dictionaries/kk").then((m) => m.kk),
  en: () => import("./dictionaries/en").then((m) => m.en),
};

// Server-only: the locale comes from the [lang] root segment.
export async function getLocale(): Promise<Locale> {
  const locale = await lang();
  if (!hasLocale(locale)) notFound();
  return locale;
}

export async function getDictionary() {
  return dictionaries[await getLocale()]();
}
