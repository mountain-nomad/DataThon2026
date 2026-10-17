# Forte brand: data from the primary source

Source: https://forte.kz/en/logo, checked 2026-10-17.
The values below come from the page's HTML and its brand data object in the page's JS bundle: swatches, gradients, logo variants and lockup groups. They are more complete than `brandbook.md`, which was written from the page's visible text. If the two disagree, this file wins. Re-check the page if a value matters for a deliverable.

## Logo: approved variants

The page's "Logotype color" block shows exactly three variants. These are the "approved set"; anything else counts as recolouring.

| Variant | Background | Logo colour | Note |
|---|---|---|---|
| Light | `#FFFFFF` | Forte Magenta `#A31551` | Shown with a 1px border |
| Dark | `#270111` | White `#FFFFFF` | |
| Magenta | `#A31551` | White `#FFFFFF` | |

The rules text says: master logotype is Forte Magenta, it reads on light and dark surfaces, keep clear space around the mark, never recolour it outside the approved set. The page gives no minimum size or exact clear-space measurement.

## Master brand (Forte)

| Name | HEX | RGB | CMYK |
|---|---|---|---|
| Forte Magenta | `#A31551` | 163/21/81 | 0/87/50/36 |
| Sky Blue | `#61CFFF` | 97/207/255 | 56/0/0/0 |
| Dark Magenta | `#4A0221` | 74/2/33 | 0/97/56/71 |
| Coral Sunshine | `#FC9385` | 252/147/133 | 0/42/47/1 |

Gradients:
- Primary, "Dark Magenta → Coral": `linear-gradient(90deg, #4A0221 0%, #FC9385 100%)`
- Secondary, "Magenta → Pink": `linear-gradient(90deg, #A31551 0%, #F03785 100%)`. **Pink = `#F03785`.** The page gives no swatch, name variant or RGB/CMYK for Pink; only this gradient stop.
- Forte Presentation key visual: `linear-gradient(115deg, #4A0221 0%, #B8335F 55%, #FC9385 100%)`. The logo icon uses the same mid tone in its own gradient: `#F99184 → #B8335F (80.5%) → #A51652`.

## Sub-brands

Each sub-brand keeps the Forte logotype and adds a descriptor in its own colour. The page's lockup grid groups them as `[Forte, Solo, Premier]`, `[Market]`, `[Business, Corporate, Leasing, Finance]`, `[Mobile]`. Market and Mobile appear only as lockups; the page shows no palette tabs for them.

| Sub-brand | Card bg / chip | Swatches | Primary gradient | Secondary gradient |
|---|---|---|---|---|
| Forte (master) | `#A31551` | Forte Magenta, Sky Blue, Dark Magenta, Coral Sunshine | Dark Magenta → Coral `#4A0221 → #FC9385` | Magenta → Pink `#A31551 → #F03785` |
| Solo | `#4A0221` / `#A31551` | Dark Magenta, Coral Sunshine, Forte Magenta, Sky Blue | Dark Magenta → Forte Magenta `#4A0221 → #A31551` | Dark Magenta → Coral `#4A0221 → #FC9385` |
| Premier | `#08342A` | Dark Green, Medium Green, Light Green, Forte Gold | Dark Green → Light Green `#08342A → #3A8171` | Medium Green → Forte Gold `#234E44 → #C9B07E` |
| Business | `#072146` | Dark Blue, Medium Blue, Light Blue, Sky Blue | Dark Blue → Sky Blue `#072146 → #61CFFF` | Sky Blue → White `#61CFFF → #FFFFFF` |
| Corporate | `#043263` | Medium Blue, Light Blue, Sky Blue, Dark Blue | Medium Blue → Sky Blue `#043263 → #61CFFF` | Dark Blue → Light Blue `#072146 → #1464A5` |
| Leasing | `#1464A5` | Light Blue, Sky Blue, Medium Blue, Dark Blue | Light Blue → Sky Blue `#1464A5 → #61CFFF` | Sky Blue → White `#61CFFF → #FFFFFF` |
| Finance | `#878787` | Medium Grey, Light Grey, Dark Grey, White Grey | Light Grey → White Grey `#C6C6C6 → #F6F6F6` | Dark Grey → Medium Grey `#3C3C3B → #878787` |

All gradients on the page are `90deg`. The Business Presentation key visual is `linear-gradient(160deg, #1464A5 0%, #072146 100%)`.

### Sub-brand swatches

| Name | HEX | RGB | CMYK | Used by |
|---|---|---|---|---|
| Dark Green | `#08342A` | 8/52/42 | 90/49/72/66 | Premier |
| Medium Green | `#234E44` | 35/78/68 | 83/43/64/47 | Premier |
| Light Green | `#3A8171` | 58/129/113 | 77/28/57/13 | Premier |
| Forte Gold | `#C9B07E` | 201/176/126 | 22/27/54/6 | Premier |
| Dark Blue | `#072146` | 7/33/70 | 100/88/43/47 | Business, Corporate, Leasing |
| Medium Blue | `#043263` | 4/50/99 | 100/83/36/23 | Business, Corporate, Leasing |
| Light Blue | `#1464A5` | 20/100/165 | 90/57/8/1 | Business, Corporate, Leasing |
| Medium Grey | `#878787` | 135/135/135 | 47/37/37/17 | Finance |
| Light Grey | `#C6C6C6` | 198/198/198 | 26/19/20/2 | Finance |
| Dark Grey | `#3C3C3B` | 60/60/59 | 66/57/55/60 | Finance |
| White Grey | `#F6F6F6` | 246/246/246 | 4/3/4/0 | Finance |

## Typography

Open Sans, with weights Light 300, Regular 400, Semibold 600, Bold 700 and Extrabold 800. This matches `brandbook.md`.
