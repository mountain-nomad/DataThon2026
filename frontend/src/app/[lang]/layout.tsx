import type { Metadata } from "next";
import { Open_Sans } from "next/font/google";
import { I18nProvider } from "@/i18n/I18nProvider";
import { locales } from "@/i18n/config";
import { getDictionary, getLocale } from "@/i18n/dictionaries";
import "../globals.css";

// Forte brand typeface. Variable font covers the brand weights 300–800.
// cyrillic-ext carries the Kazakh letters (Ә Ғ Қ Ң Ө Ұ Ү Һ І).
const openSans = Open_Sans({
  variable: "--font-open-sans",
  subsets: ["latin", "cyrillic", "cyrillic-ext"],
});

export function generateStaticParams() {
  return locales.map((lang) => ({ lang }));
}

export async function generateMetadata(): Promise<Metadata> {
  const t = await getDictionary();
  return { title: t.meta.title, description: t.meta.description };
}

export default async function RootLayout({ children }: LayoutProps<"/[lang]">) {
  const locale = await getLocale();
  return (
    <html lang={locale} data-scroll-behavior="smooth" className={`${openSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <I18nProvider key={locale} locale={locale}>
          {children}
        </I18nProvider>
      </body>
    </html>
  );
}
