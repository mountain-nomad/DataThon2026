import Image from "next/image";

// Official Forte logotype files (frontend/public/brand/Forte_logos/Logo Forte/).
// Approved variants only: magenta on white, white on dark #270111 or on magenta. Never recolour.
const LOGO = {
  magenta: "/brand/Forte_logos/Logo%20Forte/Group%202087330514%20(1).svg",
  white: "/brand/Forte_logos/Logo%20Forte/Group%202087330521.svg",
};

export function BrandMark({ variant = "magenta", height = 24 }: { variant?: keyof typeof LOGO; height?: number }) {
  // Source artwork is 731×218.
  return (
    <Image
      src={LOGO[variant]}
      alt="Forte"
      width={Math.round((height * 731) / 218)}
      height={height}
      unoptimized
      priority
    />
  );
}
