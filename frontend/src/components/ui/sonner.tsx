"use client";

import { Toaster as Sonner, type ToasterProps } from "sonner";

// Light theme only (DESIGN.md defines no dark palette). Toasts are flat printout notes:
// paper with a 1 px ink border, no shadow and no rounded corners.
const Toaster = (props: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      position="bottom-center"
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
