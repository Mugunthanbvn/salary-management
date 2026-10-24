import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

import type { components } from "@/lib/api/schema";
import { makeMe } from "@/test/fixtures";
import { server } from "@/test/msw/server";

import { LoginForm } from "./login-form";

type LoginRequest = components["schemas"]["LoginRequest"];
type LoginResponse = components["schemas"]["LoginResponse"];

const { hardNavigate, search } = vi.hoisted(() => ({
  hardNavigate: vi.fn(),
  search: { value: "" },
}));
vi.mock("@/lib/hard-navigate", () => ({ hardNavigate }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(search.value),
}));

const LOGIN_URL = "/api/v1/auth/login";

function signedIn(): LoginResponse {
  const { user, permissions } = makeMe();
  return { user, permissions };
}

async function signIn(email = "hr@acme.example", password = "correct horse") {
  render(<LoginForm />);
  await userEvent.type(screen.getByLabelText("Email"), email);
  await userEvent.type(screen.getByLabelText("Password"), password);
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginForm", () => {
  it("signs in through the API and opens Insights", async () => {
    let sent: LoginRequest | undefined;
    server.use(
      http.post<never, LoginRequest, LoginResponse>(
        LOGIN_URL,
        async ({ request }) => {
          sent = await request.json();
          return HttpResponse.json(signedIn());
        },
      ),
    );

    await signIn("hr@acme.example", "correct horse");

    await waitFor(() => expect(hardNavigate).toHaveBeenCalledWith("/insights"));
    expect(sent).toEqual({
      email: "hr@acme.example",
      password: "correct horse",
    });
  });
});
