import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/lib/api/schema";
import { makeMe } from "@/test/fixtures";
import { server } from "@/test/msw/server";

import { LoginForm } from "./login-form";

type LoginRequest = components["schemas"]["LoginRequest"];
type LoginResponse = components["schemas"]["LoginResponse"];
type Problem = components["schemas"]["Problem"];

function problem(status: number, slug: string, title: string): Problem {
  return {
    type: `https://acme.example/problems/${slug}`,
    title,
    status,
    detail: "Invalid email or password",
    instance: "/api/v1/auth/login",
    request_id: "req-1",
  };
}

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

beforeEach(() => {
  search.value = "";
});

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

  it.each([
    { next: "/employees?country=DE", opens: "/employees?country=DE" },
    { next: "//evil.example/insights", opens: "/insights" },
    { next: "https://evil.example", opens: "/insights" },
  ])(
    "after signing in with next=$next, opens $opens",
    async ({ next, opens }) => {
      search.value = new URLSearchParams({ next }).toString();
      server.use(
        http.post<never, LoginRequest, LoginResponse>(LOGIN_URL, () =>
          HttpResponse.json(signedIn()),
        ),
      );

      await signIn();

      await waitFor(() => expect(hardNavigate).toHaveBeenCalledWith(opens));
    },
  );

  it("says the email or password is wrong, without saying which", async () => {
    server.use(
      http.post<never, LoginRequest, Problem>(LOGIN_URL, () =>
        HttpResponse.json(
          problem(401, "unauthenticated", "Not authenticated"),
          {
            status: 401,
          },
        ),
      ),
    );

    await signIn("hr@acme.example", "wrong");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email or password is incorrect",
    );
    expect(screen.getByLabelText("Password")).toHaveAccessibleDescription(
      "Email or password is incorrect",
    );
    expect(hardNavigate).not.toHaveBeenCalled();
  });
});
