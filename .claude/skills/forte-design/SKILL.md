---
name: forte-design
description: ForteBank (forte.kz) brand and design system — colours, gradients, typography, logo rules and ready-made design tokens. Use whenever building or restyling any UI, page, component, chart, slide or visual for this project or for anything Forte-branded (frontend/, dashboards, demo screens, pitch materials), or when the user mentions Forte, ForteBank, the brand book, brand colours or "make it look like Forte".
---

# Forte design system

Sources:
- `references/brandbook.md` is the brand book as written from the visible text of https://forte.kz/en/logo.
- `references/primary-source.md` holds the exact values pulled from that page's data: the official Pink, the approved logo variants and all sub-brand palettes. Where the two differ, `primary-source.md` wins.

This file turns them into rules and tokens. **Brand book** below means an official value from either source. **Derived** means a choice made here to fill a gap the sources leave open (neutrals, states, most of dark mode). Keep derived values consistent, but don't present them as official Forte guidance.

## Brand idea

A rising sunrise: a new beginning, growth, progress. Designs should feel warm, optimistic and forward-looking. Gradient light rises from deep magenta into coral. For the master brand, avoid cold, grey, corporate-blue looks. Blue and grey belong to the Business, Corporate, Leasing and Finance sub-brands, not to Forte itself.

## Colour

### Master brand palette (brand book)

| Token | HEX | Role |
|---|---|---|
| `forte-magenta` | `#A31551` | Master brand colour. Logotype, primary actions, key highlights |
| `forte-dark-magenta` | `#4A0221` | Deep backgrounds, hero bands, dark-mode surfaces, strong text |
| `forte-coral` | `#FC9385` | Warm accent. Gradient end, highlights on dark, dark-mode primary |
| `forte-sky` | `#61CFFF` | Cool accent for contrast. Positive/"live" states, data series, focus |

Gradients (brand book):
- **Primary:** Dark Magenta → Coral.
  - Swatch form: `linear-gradient(90deg, #4A0221, #FC9385)`. Use it for thin bands, bars and stripes.
  - Key-visual form (Forte Presentation): `linear-gradient(115deg, #4A0221 0%, #B8335F 55%, #FC9385 100%)`. `#B8335F` is the official mid tone; the logo icon's gradient uses it too. This is `bg-hero`. Use it for hero bands and the main visual moment of a page, once or twice per screen, not on every card.
  - Contrast: white text stays ≥ 4.5:1 over roughly the first 65% (≈5.7:1 at the `#B8335F` stop) and drops to 2.2:1 on Coral. Keep text left-aligned on the dark side.
- **Secondary:** Magenta → Pink: `linear-gradient(90deg, #A31551, #F03785)`, available as `bg-hero-secondary`. **Pink = `#F03785`** (primary source; the page gives only this gradient stop, no RGB/CMYK). Use it for secondary emphasis such as promo cards, highlighted tiles, progress or badges, and in places where the primary gradient would compete with the hero.
  - Contrast: white text stays ≥ 4.5:1 over roughly the first 70% and drops to ≈3.8:1 on pure Pink. Keep body text on the Magenta side; large or bold text (≥24px, or ≥19px bold) is fine anywhere on it.

Don't add new hues to a master-brand (Forte) screen: no greens, oranges, purples or corporate blues. If you need more chart colours, use tints and shades of the four master colours plus Pink.

### Sub-brands (primary source)

Each sub-brand keeps the Forte logotype and adds a descriptor in its own colour. Each has its own palette and gradients. **Use one sub-brand's palette per screen, and never mix colour families** (for example, no Premier gold on a Business screen). Full swatches with RGB/CMYK are in `references/primary-source.md`.

| Sub-brand | Key colour | Primary gradient | Secondary gradient |
|---|---|---|---|
| Solo | Dark Magenta `#4A0221` (+ master palette) | `#4A0221 → #A31551` | `#4A0221 → #FC9385` |
| Premier | Dark Green `#08342A`, Forte Gold `#C9B07E` | `#08342A → #3A8171` | `#234E44 → #C9B07E` |
| Business | Dark Blue `#072146` | `#072146 → #61CFFF` | `#61CFFF → #FFFFFF` |
| Corporate | Medium Blue `#043263` | `#043263 → #61CFFF` | `#072146 → #1464A5` |
| Leasing | Light Blue `#1464A5` | `#1464A5 → #61CFFF` | `#61CFFF → #FFFFFF` |
| Finance | Medium Grey `#878787` | `#C6C6C6 → #F6F6F6` | `#3C3C3B → #878787` |

The current `frontend/` tokens are master brand only. To build a sub-brand look, add that sub-brand's palette as a separate token set rather than editing the master tokens. Market and Mobile appear as lockups on the page but have no published palette, so ask before styling them.

### Contrast rules (derived, checked against WCAG)

- White on Magenta ≈ 7.5:1 ✅ and white on Dark Magenta ≈ 16:1 ✅, so these work for button text and hero text.
- Dark Magenta on Coral ≈ 7.3:1 ✅. This is the primary button in dark mode.
- Magenta text on white ≈ 7.5:1 ✅. Use it for links and emphasised text in light mode.
- **Coral and Sky Blue fail as text on white** (≈2.2:1 and ≈1.7:1). In light mode use them only as fills, dots, bars or borders, always paired with a text label.
- On the primary gradient, white text stays above 4.5:1 only over roughly the first 60% (the dark-magenta side). Keep text left-aligned on that side.
- Magenta as a fill on Dark-Magenta-black surfaces is too weak (≈2.6:1). In dark mode use Coral for primary actions and links.

### Semantic tokens (derived)

Implemented in `frontend/src/app/globals.css` as CSS variables and exposed to Tailwind v4 through `@theme inline`. Use the Tailwind names in markup: `bg-surface`, `text-muted`, `border-border`, `bg-primary text-primary-foreground`, `bg-hero`, `bg-hero-secondary`, and so on. Never hard-code hex values in components.

| Token | Light | Dark |
|---|---|---|
| `background` | `#FAF6F8` (warm off-white) | `#270111` (official dark logo background) |
| `surface` | `#FFFFFF` | `#360A1F` |
| `surface-muted` | `#F5EDF1` | `#45122B` |
| `foreground` | `#2B0716` | `#F8EEF3` |
| `muted` | `#6E5663` | `#C4A9B7` |
| `border` | `#EBDFE5` | `#5C1D3C` |
| `primary` / `primary-foreground` | Magenta / white | Coral / Dark Magenta |
| `primary-hover` | `#8A1145` | `#FDA99E` |
| `accent` | Sky `#61CFFF` | Sky `#61CFFF` |
| `danger-bg` / `danger-fg` | `#FDECEA` / `#8A1145` | `#4A0F28` / `#FC9385` |

Errors use magenta/coral tones rather than an off-brand red. Pair them with an icon or a clear message so they don't read as decoration.

## Typography (brand book)

- **Open Sans only**, for UI, display, body and captions. In Next.js: `next/font/google` → `Open_Sans({ subsets: ["latin", "cyrillic"], variable: "--font-open-sans" })`. Include **cyrillic**, because the product is used in Kazakhstan (RU/KZ text).
- Weights: 300 Light · 400 Regular · 600 Semibold · 700 Bold · 800 Extrabold. Don't use 500 or 900.
- Suggested scale (derived): display 40–48px/800 · H1 28–32px/700 · H2 20px/700 · section label 12–13px/600 uppercase with 0.06em letter spacing · body 15–16px/400 · caption 13px/400 in `muted`.
- Numbers in tables and metrics: `tabular-nums`. Use monospace only for raw code or JSON.

## Logo (brand book + primary source)

- The master logotype is **Forte Magenta**. Keep clear space around it. Never stretch it, never add effects, and never recolour it outside the approved set.
- **The approved set is exactly three variants:**

  | Background | Logo |
  |---|---|
  | White `#FFFFFF` | Forte Magenta `#A31551` |
  | Dark `#270111` | White |
  | Forte Magenta `#A31551` | White |

  On any dark or gradient surface the logo is **white**: never Coral, Sky or a gradient fill. In dark mode, switch to the white variant.
- **Never redraw or approximate the logo** in SVG or CSS. Use the official files from https://forte.kz/docs/forte-logos.zip and put them in `frontend/public/brand/`. Until they're there, use a plain text placeholder clearly marked as one (see `frontend/src/components/BrandMark.tsx`).
- Sub-brand lockups (Solo, Premier, Business, Corporate, Leasing, Finance, plus Market and Mobile) keep the Forte logotype and add a descriptor in the sub-brand's colour. Their palettes are in the Sub-brands section above. Use the official lockup files; don't typeset the descriptor yourself.

## Layout and components (derived, applied in `frontend/`)

- Warm off-white page, white surface cards, 1px `border`, radius 16px for cards and 12px for controls, very soft shadow (`shadow-sm` at most). The gradient carries the visual weight, not the shadows.
- One **hero band** with the primary gradient at the top of a page: an Extrabold title and a short subtitle on the dark side.
- Primary button: pill-shaped (`rounded-full`), `bg-primary text-primary-foreground`, Semibold. Secondary button: `border-border` outline. Focus ring: `accent` (sky).
- Status: a Sky dot means live/ok, a Coral dot means down/attention, and the dot always comes with a text label.
- Charts and probabilities: Magenta for the main series, then Sky, Coral, Dark Magenta. Light-mode bars sit on a `surface-muted` track.
- Use generous whitespace and keep it calm. One accent moment per section.

## Legal copy

Forte-facing screens that show payment cards must carry the brand book's disclaimer (see `references/brandbook.md` §8). Contacts and links are in §7. Don't invent licence numbers or contact details.

## Checklist before finishing a UI change

1. Only tokens are used; there are no raw hex values in components.
2. Open Sans is loaded with the cyrillic subset, and only brand weights are used.
3. Light and dark mode both pass the contrast rules above.
4. There's no fake logo, and any placeholder is marked as one.
5. Gradients are used sparingly: primary for the hero, secondary for supporting emphasis, never both competing in one section. Text sits on the dark side.
6. The logo (or placeholder) uses only an approved variant: Magenta on light, white on dark, magenta or gradient backgrounds.
7. One colour family per screen: master Forte, or a single sub-brand's palette.
