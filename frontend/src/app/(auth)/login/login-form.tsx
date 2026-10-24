"use client";

import { useState, useSyncExternalStore, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import { safeNextPath } from "@/lib/auth-redirect";
import { hardNavigate } from "@/lib/hard-navigate";

const ERROR_ID = "login-error";

const noSubscription = () => () => {};

/**
 * False in the server HTML, true once React runs in the browser. Until then "Sign in" is
 * disabled: a click would be the browser's own form submit, not the API call.
 */
function useHydrated(): boolean {
  return useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
}

function text(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === "string" ? value : "";
}

/** What to tell the person when the API refuses the sign-in. */
function errorMessage(response: Response): string {
  // Same words for an unknown email and a wrong password, like the API.
  if (response.status === 401) return "Email or password is incorrect";
  if (response.status === 429) return tooManyAttempts(response);
  return COULD_NOT_SIGN_IN;
}

const COULD_NOT_SIGN_IN = "Couldn't sign you in. Try again in a moment.";

/** 5 failures in 15 minutes lock the email; Retry-After says for how many seconds. */
function tooManyAttempts(response: Response): string {
  const seconds = Number(response.headers.get("Retry-After"));
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "Too many attempts. Try again later.";
  }
  const minutes = Math.ceil(seconds / 60);
  return `Too many attempts. Try again in ${minutes} ${minutes === 1 ? "minute" : "minutes"}.`;
}

/**
 * The page to open after signing in, from /login?next=…. Only a path on this site: an open
 * redirect could take someone who just signed in to a look-alike site. Read when the form is
 * sent, not while rendering, so the page prerenders without waiting for the URL.
 */
function nextPage(): string {
  return safeNextPath(new URLSearchParams(window.location.search).get("next"));
}

/**
 * Email and password, posted with a client fetch through the /api rewrite, never a Server
 * Action: the browser itself must receive FastAPI's Set-Cookie (docs/17-deployment.md §3.4).
 */
export function LoginForm() {
  const hydrated = useHydrated();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    setError(null);
    try {
      const { data, response } = await api.POST("/api/v1/auth/login", {
        body: { email: text(form, "email"), password: text(form, "password") },
      });
      if (data) {
        hardNavigate(nextPage());
        return;
      }
      setError(errorMessage(response));
    } catch {
      // The network failed before the API could answer.
      setError(COULD_NOT_SIGN_IN);
    }
    setPending(false);
  }

  const describedBy = error ? ERROR_ID : undefined;
  return (
    // method="post": even a submit that slips past React never puts the password in a URL.
    <form
      method="post"
      onSubmit={(event) => void onSubmit(event)}
      className="flex flex-col gap-5"
    >
      <div className="flex flex-col gap-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          required
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
        />
      </div>
      {error ? (
        <p id={ERROR_ID} role="alert" className="text-[15px] text-ink red-pen">
          {error}
        </p>
      ) : null}
      <Button
        type="submit"
        disabled={!hydrated || pending}
        className="w-full sm:w-auto"
      >
        {pending ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}
