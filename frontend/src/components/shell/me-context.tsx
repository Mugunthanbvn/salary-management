"use client";

import type { ReactNode } from "react";

import type { Me, Permission } from "@/lib/permissions";

export function MeProvider(props: { me: Me; children: ReactNode }) {
  void props;
  return null;
}

export function useMe(): Me & { can: (permission: Permission) => boolean } {
  throw new Error("useMe is not implemented yet");
}
