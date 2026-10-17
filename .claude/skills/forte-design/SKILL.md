---
name: forte-design
description: ForteBank (forte.kz) brand and design system — colours, gradients, typography (Open Sans), official logo files and the project's approved white, minimal look. Use whenever building or restyling any UI, page, component, chart, slide or visual for this project or for anything Forte-branded (frontend/, landing, dashboards, demo screens, pitch materials), or when the user mentions Forte, ForteBank, the brand book, brand colours or "make it look like Forte".
---

# Forte design system

**Source:** `references/brandbook.md`, the master-brand part of https://forte.kz/en/logo. A copy also sits at the repo root as `forte-brandbook.md`; keep the two identical.

This file turns the brand book into rules for this project. **Brand book** means an official value. **Derived** means a choice made here to fill a gap (neutrals, states, layout). Don't present derived values as official Forte guidance.

## Project direction (approved by the user — these override everything below)

1. **The page background is white.** Neutrals are the greys forte.kz uses in its own UI: text `#1D1D1D`, secondary text `#6C6C6C`, borders `#EAEBEF`, subtle fills `#F7F6F6`.
2. **Minimal, with magenta as an accent only.** Use it for the logo, primary buttons, small labels (such as section numbers) and the one highlighted data series. Don't tint backgrounds, borders or text pink or red, and don't use magenta for big numbers or headings.
3. **No large gradient blocks**: no gradient hero, CTA band or dark footer. The brand gradient appears at most once per page, as a thin line (`bg-gradient-primary`).
4. **Light theme only.** There's no dark mode; `color-scheme: light` is set.
5. **Only Forte's main colours**: Forte Magenta, Sky Blue, Dark Magenta, Coral Sunshine, plus the two brand gradients. No sub-brand colours and no other hues. The neutral greys below are UI greys, not brand colours.
6. **Open Sans is the primary typeface**, with brand weights only.
7. **The logo is always the official file.** Never set "forte" as text, and never redraw it.

The current `frontend/` follows all of this. Before adding UI, look at `frontend/src/app/page.tsx` (landing) and `frontend/src/app/dashboard/page.tsx` as the reference implementation.

## Colour

### Main colours (brand book §3) — the only brand colours

| Token | Colour | HEX | Role here |
|---|---|---|---|
| `forte-magenta` | Forte Magenta | `#A31551` | Master brand colour and the single accent: logo, primary buttons, section numbers, highlighted series, links |
| `forte-sky` | Sky Blue | `#61CFFF` | Focus ring and the "live/ok" status dot. Never use it as text on white |
| `forte-coral` | Coral Sunshine | `#FC9385` | "Down/attention" status dot and the end of the primary gradient. Never use it as text on white |
| `forte-dark-magenta` | Dark Magenta | `#4A0221` | Start of the primary gradient |

### Gradients (brand book §3.2)

| Name | Value | Utility | Use here |
|---|---|---|---|
| Primary: Dark Magenta → Coral | `90deg #4A0221 → #FC9385` | `bg-gradient-primary` | ✅ One thin rule per page (for example, above the steps) |
| Secondary: Magenta → Pink | `90deg #A31551 → #F03785` | `bg-gradient-secondary` | Only if the user asks |

Pink `#F03785` exists only as the end stop of the secondary gradient; never use it on its own. If a gradient surface ever carries text, keep the text on the dark start of the gradient.

### Semantic tokens (derived)

Defined in `frontend/src/app/globals.css` and exposed to Tailwind v4 through `@theme inline`. Use the Tailwind names (`bg-surface`, `text-muted`, `border-border`, `bg-primary text-primary-foreground`, `bg-gradient-primary`…). **Never hard-code hex values in components.**

| Token | Value | Contrast on white | Source |
|---|---|---|---|
| `background`, `surface` | `#FFFFFF` | — | Project direction |
| `surface-muted` | `#F7F6F6` | — | forte.kz UI fill |
| `foreground` | `#1D1D1D` | 16.9:1 | forte.kz body text |
| `muted` | `#6C6C6C` | 5.3:1 | forte.kz UI grey |
| `border` | `#EAEBEF` | — | forte.kz UI border |
| `primary` / `primary-foreground` | `#A31551` / `#FFFFFF` | 7.5:1 | Brand book |
| `primary-hover` | `#8A1145` | 9.4:1 | Derived |
| `accent` | `#61CFFF` | 1.8:1 (fill only) | Brand book |
| `danger-bg` / `danger-fg` | `#FDF1F4` / `#8A1145` | — | Derived; errors use the brand's magenta, not off-brand red |

## Typography (brand book)

- **Open Sans is the primary typeface**, for UI, display, body and captions. It's loaded in `layout.tsx` with `next/font/google` → `Open_Sans({ subsets: ["latin", "cyrillic"], variable: "--font-open-sans" })` and set as Tailwind's `--font-sans` and on `body`, so every element defaults to it. Keep **cyrillic**, because the product is used in Kazakhstan.
- **Weights: 300 · 400 · 600 · 700 · 800 only.** Don't use `font-medium` (500), `font-black` (900), `font-thin` or `font-extralight`.
- Scale (derived, as used on the landing):

  | Role | Style |
  |---|---|
  | Display / hero | 40–48px, 800, tight tracking, `foreground` |
  | Section title | 28–32px, 700 |
  | Card / step title | 20px, 700 |
  | Lead | 18px, 300, `muted` |
  | Section label | 12px, 600, uppercase, `0.06em` letter spacing, `muted`; its number in `primary` |
  | Body | 15–16px, 400 |
  | Caption | 13px, 400, `muted` |

- Numbers in metrics and tables use `tabular-nums`. Monospace is only for raw JSON or code.

## Logo (brand book §2)

- **Approved variants:** the Forte Magenta logo on white (the one used on this project), or the white logo on Forte Magenta. Never recolour, stretch or add effects, and keep clear space around it.
- **Always use the official files** from `frontend/public/brand/Forte_logos/Logo Forte/`, through `<BrandMark variant="magenta" | "white" height={…} />` (`frontend/src/components/BrandMark.tsx`). The artwork is 731×218. The folder name contains a space, so URL-encode it in `src`.
- The other folders in `Forte_logos/` are sub-brand lockups. They are not used here.
- Never typeset "forte" as text in place of the logo.

## Layout and components (derived — the approved look)

- **Surfaces:** white page and white cards with a 1px `border`. Radius is 16px for cards and 12px for controls. **No shadows, no blur, no glass effects.** Whitespace and type carry the hierarchy, with large vertical gaps between sections (`gap-24`/`gap-32`).
- **Header:** white, a bottom `border`, the magenta logo on the left, muted text nav, one primary pill CTA on the right.
- **Hero:** white and type-led. An Extrabold headline, a Light muted lead, one primary pill button and one outline secondary. If there's a supporting card on the right, it shows real data.
- **Sections:** start each with a numbered label (`01 · How it works`), echoing the numbered sections on forte.kz's brand page. Below it, a 28–32px Bold title and an optional muted lead.
- **Buttons:** pill shape (`rounded-full`), Semibold. Primary is `bg-primary text-primary-foreground`; secondary is a `border-border` outline. The focus ring is `accent`. Use the helpers in `components/Card.tsx`: `buttonClass`, `buttonPrimaryLinkClass`, `buttonSecondaryClass`.
- **Status:** a Sky dot means live/ok, a Coral dot means down. The dot always comes with a text label.
- **Charts and probability bars:** the highlighted series is `bg-primary` and the rest are neutral (`bg-muted/40`), on a `surface-muted` track. Bring in Sky, Coral or Dark Magenta only when several series genuinely need to be told apart.
- **Footer:** white, a top `border`, the magenta logo, a muted honest note ("Prototype built for DataThon 2026. Not an official ForteBank product or service."), and text links.

### Content rules (keep it from looking like AI slop)

- Every number, metric and status on a page comes from the API, never a placeholder figure. When data is missing, say so honestly (for example, "The backend isn't reachable. Start the services with make dev.").
- No invented stats, testimonials, partner logos, slogans or marketing claims. The copy describes what the system actually does.
- No emoji, decorative icon grids, gradient text, blobs or entrance animations. Smooth scrolling only under `prefers-reduced-motion: no-preference`.
- Don't use repeated identical cards when plain text columns will do.

## Legal copy (brand book §6–7)

Screens that show payment cards must carry the disclaimer in §7. Use contacts and links only from §6. Never invent licence numbers or contact details, and never present the prototype as an official ForteBank product.

## Checklist before finishing a UI change

1. The background is white; magenta appears only as an accent; there are no gradient blocks and at most one `bg-gradient-primary` line.
2. Only tokens are used: no raw hex in components (comments excepted).
3. Everything is in Open Sans, with weights 300/400/600/700/800 only; monospace only for raw JSON.
4. The logo is the official master file through `BrandMark`, in an approved variant.
5. Text passes the contrast in the token table; Sky and Coral are never used as text on white.
6. All data shown is real or honestly empty; there's no filler copy.
7. Only Forte's four main colours and the two brand gradients; no sub-brand or other hues.
8. Before finishing, check the page at 390px width with no horizontal scroll, and the build passes.
