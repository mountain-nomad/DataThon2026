"use client";

import { useI18n } from "@/i18n/I18nProvider";
import type { LegalBasis as Basis } from "@/lib/types";

// The link from a detected violation to public sources (task §6): the violation type, each
// clause with its source and link, and the mapping's own limitations (shown before the source).
// The level cap (max_severity) and show_source come from the mapping and are never overridden.
// Source texts are shown as written in the mapping; only the labels are translated. Nothing is
// shown as legally verified unless the mapping says so.
export function LegalBasis({ basis }: { basis?: Basis }) {
  const { t } = useI18n();
  const tl = t.legal;
  const limitations = basis?.limitations && (
    <p className="text-xs text-muted">
      <span className="font-semibold">{tl.limitations}:</span> {basis.limitations}
    </p>
  );
  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-[0.06em] text-muted">{tl.title}</p>
      {!basis ? (
        <p className="text-sm text-muted">{tl.notMapped}</p>
      ) : (
        <>
          {(basis.name || basis.mappingStatus) && (
            <p className="text-sm">
              {basis.name && <span className="font-semibold">{basis.name}</span>}
              {basis.mappingStatus && (
                <span className="text-muted">
                  {basis.name ? " · " : ""}
                  {tl.mapping[basis.mappingStatus] ?? basis.mappingStatus}
                </span>
              )}
            </p>
          )}
          {basis.maxSeverity === "warning" && <p className="text-xs text-muted">{tl.warningCap}</p>}
          {/* The mapping's rule: limitations always come first, before the source. */}
          {limitations}
          {!basis.showSource ? (
            <p className="text-sm text-muted">{tl.sourceHidden}</p>
          ) : basis.clauses.length === 0 ? (
            <p className="text-sm text-muted">{tl.notMapped}</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {basis.clauses.map((c) => (
                <li key={c.ruleId} className="flex flex-col gap-0.5 border-l-2 border-border pl-3 text-sm">
                  <p>
                    {c.source.url ? (
                      <a
                        href={c.source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline-offset-2 hover:underline"
                      >
                        {c.source.title}
                      </a>
                    ) : (
                      c.source.title
                    )}
                    <span className="text-muted">, {c.clause}</span>
                  </p>
                  {c.summary && <p className="text-muted">{c.summary}</p>}
                  {(!c.humanVerified || !c.binding) && (
                    <p className="text-xs text-muted">
                      {[!c.binding && tl.nonBinding, !c.humanVerified && tl.notVerified].filter(Boolean).join(" · ")}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
