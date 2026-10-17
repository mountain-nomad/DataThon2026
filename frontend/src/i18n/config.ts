// Locales. Russian is the primary one and lives at unprefixed URLs (/, /demo-inference);
// the others are prefixed (/kk/..., /en/...). proxy.ts rewrites unprefixed paths to /ru/...

export const locales = ["ru", "kk", "en"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "ru";

// Labels in the language switcher, each in its own language.
export const localeLabels: Record<Locale, string> = { ru: "Рус", kk: "Қаз", en: "Eng" };

export const hasLocale = (value: string): value is Locale => (locales as readonly string[]).includes(value);

// "/demo-inference" -> "/demo-inference" (ru), "/en/demo-inference" (en).
export function localePath(locale: Locale, path: string): string {
  if (locale === defaultLocale) return path;
  return path === "/" ? `/${locale}` : `/${locale}${path}`;
}

export type Plural = { one: string; few?: string; many?: string; other: string };

export function plural(locale: Locale, n: number, forms: Plural): string {
  const rule = new Intl.PluralRules(locale).select(n) as keyof Plural;
  return fmt(forms[rule] ?? forms.other, { n });
}

export function fmt(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(vars[key] ?? `{${key}}`));
}
