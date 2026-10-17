---
name: forte-design
description: ForteBank (forte.kz) brand and design system — colours, gradients, typography (Open Sans), official logo files and the project's approved white, minimal look. Use whenever building or restyling any UI, page, component, chart, slide or visual for this project or for anything Forte-branded (frontend/, landing, dashboards, demo screens, pitch materials), or when the user mentions Forte, ForteBank, the brand book, brand colours or "make it look like Forte".
---

# Forte design system

**Source:** `references/brandbook.md`, the brand book from https://forte.kz/en/logo, including exact values taken from the page data and the logo files. A copy also sits at the repo root as `forte-brandbook.md`; keep the two identical.

This file turns the brand book into rules for this project. **Brand book** means an official value. **Derived** means a choice made here to fill a gap (neutrals, states, layout). Don't present derived values as official Forte guidance.

## Project direction (approved by the user — these override everything below)

1. **The page background is white.** Neutrals are the greys forte.kz uses in its own UI: text `#1D1D1D`, secondary text `#6C6C6C`, borders `#EAEBEF`, subtle fills `#F7F6F6`.
2. **Minimal, with magenta as an accent only.** Use it for the logo, primary buttons, small labels (such as section numbers) and the one highlighted data series. Don't tint backgrounds, borders or text pink or red, and don't use magenta for big numbers or headings.
3. **No large gradient blocks**: no gradient hero, CTA band or dark footer. The brand gradient appears at most once per page, as a thin swatch-form line (`bg-hero-line`).
4. **Light theme only.** There's no dark mode; `color-scheme: light` is set.
5. **Open Sans is the primary typeface**, with brand weights only.
6. **The logo is always the official file.** Never set "forte" as text, and never redraw it.

The current `frontend/` follows all of this. Before adding UI, look at `frontend/src/app/page.tsx` (landing) and `frontend/src/app/dashboard/page.tsx` as the reference implementation.

## Colour

### Master brand palette (brand book)

| Token | HEX | Role here |
|---|---|---|
| `forte-magenta` | `#A31551` | The single accent: logo, primary buttons, section numbers, highlighted series, links |
| `forte-sky` | `#61CFFF` | Focus ring and the "live/ok" status dot. Never use it as text on white |
| `forte-coral` | `#FC9385` | "Down/attention" status dot, and the end of the gradient line. Never use it as text on white |
| `forte-dark-magenta` | `#4A0221` | The start of the gradient line. Otherwise unused on white pages |

Pink `#F03785` exists only as the end of the secondary gradient, and there's no RGB/CMYK for it.

**Gradients (brand book)**, all available as utilities in `globals.css`:

| Name | Value | Utility | Use here |
|---|---|---|---|
| Primary, swatch form | `90deg #4A0221 → #FC9385` | `bg-hero-line` | ✅ One thin rule per page (for example, above the steps) |
| Primary, key visual | `115deg #4A0221 0% → #B8335F 55% → #FC9385 100%` | `bg-hero` | ❌ Not used unless the user asks |
| Secondary | `90deg #A31551 → #F03785` | `bg-hero-secondary` | ❌ Not used unless the user asks |

If a gradient surface ever does carry text, white text passes 4.5:1 only over the dark ~60% of the primary gradient and ~70% of the secondary one. Keep text on that side.

### Sub-brands (brand book §3)

Each sub-brand has its own palette, gradients and lockup files (full table in `references/brandbook.md` §3.2 and §2.3). **One colour family per screen.** This project is master-brand Forte, so don't bring in Premier green/gold or the Business/Corporate/Leasing blues. To build a sub-brand look, add its palette as a separate token set and use its own lockup file.

### Semantic tokens (derived)

Defined in `frontend/src/app/globals.css` and exposed to Tailwind v4 through `@theme inline`. Use the Tailwind names (`bg-surface`, `text-muted`, `border-border`, `bg-primary text-primary-foreground`, `bg-hero-line`…). **Never hard-code hex values in components.**

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

- **Approved variants only:** magenta logo on white, white logo on `#270111`, white logo on Magenta. Never recolour, stretch or add effects, and keep clear space around it.
- **Always use the official files** in `frontend/public/brand/Forte_logos/` through `<BrandMark variant="magenta" | "white" height={…} />` (`frontend/src/components/BrandMark.tsx`). The master artwork is 731×218.
- Each logo folder holds a full-colour file (for light backgrounds) and a white file (for dark backgrounds). The file-by-file map for every sub-brand, including Market and Mobile, is in `references/brandbook.md` §2.3. Folder names contain spaces; URL-encode them in `src`.
- Never typeset "forte" or a sub-brand descriptor as text in place of the logo.

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

## Legal copy (brand book §7–8)

Screens that show payment cards must carry the disclaimer in §8. Use contacts and links only from §7. Never invent licence numbers or contact details, and never present the prototype as an official ForteBank product.

## Checklist before finishing a UI change

1. The background is white; magenta appears only as an accent; there are no gradient blocks and at most one `bg-hero-line`.
2. Only tokens are used: no raw hex in components (comments excepted).
3. Everything is in Open Sans, with weights 300/400/600/700/800 only; monospace only for raw JSON.
4. The logo is the official file through `BrandMark`, in an approved variant.
5. Text passes the contrast in the token table; Sky and Coral are never used as text on white.
6. All data shown is real or honestly empty; there's no filler copy.
7. One colour family per screen (master Forte).
8. Before finishing, check the page at 390px width with no horizontal scroll, and the build passes.
