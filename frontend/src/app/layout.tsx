import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible_Next, Source_Serif_4 } from "next/font/google";
import { NuqsAdapter } from "nuqs/adapters/next/app";

import { Toaster } from "@/components/ui/sonner";

import "./globals.css";

// Body, tables, labels and buttons (docs/design/DESIGN.md "Type").
// next/font has no fallback metrics for it yet, so it can't size-adjust a fallback font.
const sans = Atkinson_Hyperlegible_Next({
  variable: "--font-atkinson",
  subsets: ["latin"],
  adjustFontFallback: false,
  fallback: ["system-ui", "sans-serif"],
});

// Page titles, section questions, big figures and italic margin notes.
const serif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  style: ["normal", "italic"],
  axes: ["opsz"],
});

export const metadata: Metadata = {
  title: { default: "ACME Pay", template: "%s · ACME Pay" },
  description: "Salary management for ACME's HR team",
};

export const viewport: Viewport = {
  // Lets the fixed phone bars use env(safe-area-inset-*) on notched screens.
  viewportFit: "cover",
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${sans.variable} ${serif.variable}`}>
      <body className="min-h-dvh">
        {/* Filter, sort and paging state lives in the URL (docs/13-frontend-ux.md §3.2). */}
        <NuqsAdapter>{children}</NuqsAdapter>
        <Toaster />
      </body>
    </html>
  );
}
