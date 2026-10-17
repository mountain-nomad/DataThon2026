// PLACEHOLDER — not the Forte logo. Brand rules forbid redrawing the logotype:
// drop the official SVG from https://forte.kz/docs/forte-logos.zip into public/brand/
// and replace this with <Image src="/brand/forte-logo.svg" ... />.
// Approved variants only: Magenta on light, white on dark (never coral/sky).
export function BrandMark() {
  return (
    <span className="text-xl font-extrabold tracking-tight text-forte-magenta dark:text-white">
      forte
    </span>
  );
}
