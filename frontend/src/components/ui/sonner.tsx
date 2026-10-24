"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

// Clears the phone bottom bar (3.5rem + safe-area inset, components/shell/bottom-nav.tsx).
// Used at every width: Sonner's mobile breakpoint (600 px) is not the bar's (640 px).
const ABOVE_BOTTOM_BAR = "calc(3.5rem + env(safe-area-inset-bottom) + 8px)";

// Light theme only (DESIGN.md defines no dark palette). Toasts are flat printout notes:
// paper with a 1 px ink border, no shadow and no rounded corners.
const Toaster = (props: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      position="bottom-center"
      offset={{ bottom: ABOVE_BOTTOM_BAR }}
      mobileOffset={{ bottom: ABOVE_BOTTOM_BAR }}
      className="toaster group"
      style={
        {
          "--normal-bg": "var(--color-paper)",
          "--normal-text": "var(--color-ink)",
          "--normal-border": "var(--color-ink)",
          "--border-radius": "0px",
        } as React.CSSProperties
      }
      toastOptions={{
        style: {
          boxShadow: "none",
          fontFamily: "var(--font-sans)",
          fontSize: "15px",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
