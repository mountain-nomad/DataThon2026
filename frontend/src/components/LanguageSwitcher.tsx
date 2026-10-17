"use client";

import { useEffect, useRef, useState } from "react";
import { localeLabels, locales } from "@/i18n/config";
import { useI18n } from "@/i18n/I18nProvider";

function Chevron({ up }: { up: boolean }) {
  return (
    <svg viewBox="0 0 12 12" aria-hidden className={`size-3 text-muted transition-transform ${up ? "rotate-180" : ""}`}>
      <path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// Disclosure dropdown: the bordered box grows downward to list the other languages, and its
// border turns Forte Magenta on hover, focus and while open. Choosing a language translates the
// page in place (see I18nProvider.setLocale); `path` is the current route without a locale
// prefix, used to rewrite the URL.
export function LanguageSwitcher({ path }: { path: string }) {
  const { locale, t, setLocale } = useI18n();
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      if (!boxRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="relative h-10 w-[76px] shrink-0">
      <div
        ref={boxRef}
        className={`absolute inset-x-0 top-0 z-30 rounded-xl border bg-surface transition-colors focus-within:border-primary hover:border-primary ${
          open ? "border-primary" : "border-border"
        }`}
      >
        <button
          type="button"
          aria-expanded={open}
          aria-controls="language-list"
          aria-label={`${t.nav.language}: ${localeLabels[locale]}`}
          onClick={() => setOpen((v) => !v)}
          className="flex h-[38px] w-full items-center justify-between gap-1 rounded-xl px-3 text-sm font-semibold focus-visible:outline-none"
        >
          {localeLabels[locale]}
          <Chevron up={open} />
        </button>
        {open && (
          <ul id="language-list" className="flex flex-col pb-1.5">
            {locales
              .filter((l) => l !== locale)
              .map((l) => (
                <li key={l}>
                  <button
                    type="button"
                    lang={l}
                    onClick={() => {
                      setOpen(false);
                      setLocale(l, path);
                    }}
                    className="block w-full px-3 py-1.5 text-left text-sm text-foreground hover:text-primary focus-visible:text-primary focus-visible:outline-none"
                  >
                    {localeLabels[l]}
                  </button>
                </li>
              ))}
          </ul>
        )}
      </div>
    </div>
  );
}
