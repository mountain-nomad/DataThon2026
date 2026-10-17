import type { Metadata } from "next";
import { Open_Sans } from "next/font/google";
import "./globals.css";

// Forte brand typeface. Variable font covers the brand weights 300–800.
const openSans = Open_Sans({
  variable: "--font-open-sans",
  subsets: ["latin", "cyrillic"],
});

export const metadata: Metadata = {
  title: "Cash Operations Monitoring · DataThon 2026",
  description: "AI-powered video monitoring for cash operations.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${openSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
