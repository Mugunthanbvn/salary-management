"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api/client";
import { AFTER_LOGIN_PATH } from "@/lib/auth-redirect";
import { hardNavigate } from "@/lib/hard-navigate";

function text(form: FormData, name: string): string {
  const value = form.get(name);
  return typeof value === "string" ? value : "";
}

/**
 * Email and password, posted with a client fetch through the /api rewrite, never a Server
 * Action: the browser itself must receive FastAPI's Set-Cookie (docs/17-deployment.md §3.4).
 */
export function LoginForm() {
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setPending(true);
    const { data } = await api.POST("/api/v1/auth/login", {
      body: { email: text(form, "email"), password: text(form, "password") },
    });
    if (data) {
      hardNavigate(AFTER_LOGIN_PATH);
      return;
    }
    setPending(false);
  }

  return (
    <form
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
        />
      </div>
      <Button type="submit" disabled={pending} className="w-full sm:w-auto">
        {pending ? "Signing in…" : "Sign in"}
      </Button>
    </form>
  );
}
