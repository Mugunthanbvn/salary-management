"use client";

import { ChevronDownIcon } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api/client";
import { hardNavigate } from "@/lib/hard-navigate";
import { ROLE_LABELS } from "@/lib/roles";

import { useMe } from "./me-context";

/**
 * Ends the session through the API (it clears the httpOnly cookie), then reloads at /login.
 * A 401 means the session had already ended, which is just as good.
 */
async function signOut() {
  try {
    const { response } = await api.POST("/api/v1/auth/logout");
    if (response.ok || response.status === 401) {
      hardNavigate("/login");
      return;
    }
  } catch {
    // The network failed; the session is still on, so say so below.
  }
  toast.error("Couldn't sign you out. Try again.");
}

/** The signed-in person's menu in the top bar, on every screen size. */
export function AccountMenu() {
  const me = useMe();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger className="inline-flex min-h-11 max-w-[45vw] cursor-pointer items-center gap-1 rounded-control px-2 text-sm text-ink-2 hover:text-ink sm:max-w-none">
        <span className="truncate">{me.user.full_name}</span>
        <ChevronDownIcon aria-hidden="true" className="size-4 shrink-0" />
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuLabel>
          <span className="block font-bold text-ink">{me.user.full_name}</span>
          <span className="block">
            {ROLE_LABELS[me.user.role]}, {me.user.email}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {me.can("IMPORT") ? (
          <DropdownMenuItem asChild>
            <Link href="/employees/import" className="no-underline">
              Import employees
            </Link>
          </DropdownMenuItem>
        ) : null}
        <DropdownMenuItem onSelect={() => void signOut()}>
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
