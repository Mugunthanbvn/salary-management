import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { renderToString } from "react-dom/server";
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

const { hardNavigate } = vi.hoisted(() => ({ hardNavigate: vi.fn() }));
vi.mock("@/lib/hard-navigate", () => ({ hardNavigate }));

/** The page the proxy sent the person from, as /login?next=… in the address bar. */
function openLoginPage(search = "") {
  window.history.replaceState(null, "", `/login${search}`);
}

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
  openLoginPage();
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
      openLoginPage(`?${new URLSearchParams({ next }).toString()}`);
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

  it.each([
    {
      retryAfter: "900",
      message: "Too many attempts. Try again in 15 minutes.",
    },
    { retryAfter: "61", message: "Too many attempts. Try again in 2 minutes." },
    { retryAfter: "45", message: "Too many attempts. Try again in 1 minute." },
    { retryAfter: null, message: "Too many attempts. Try again later." },
  ])(
    "after too many failures (Retry-After: $retryAfter) says $message",
    async ({ retryAfter, message }) => {
      server.use(
        http.post<never, LoginRequest, Problem>(LOGIN_URL, () =>
          HttpResponse.json(problem(429, "rate-limited", "Too many requests"), {
            status: 429,
            headers: retryAfter ? { "Retry-After": retryAfter } : {},
          }),
        ),
      );

      await signIn();

      expect(await screen.findByRole("alert")).toHaveTextContent(message);
    },
  );

  it.each([
    {
      failure: "the API fails",
      reply: () =>
        HttpResponse.json<Problem>(
          {
            type: "about:blank",
            title: "Internal Server Error",
            status: 500,
            instance: "/api/v1/auth/login",
          },
          { status: 500 },
        ),
    },
    { failure: "the network fails", reply: () => HttpResponse.error() },
  ])(
    "says sign-in didn't work when $failure, and lets you retry",
    async ({ reply }) => {
      server.use(http.post(LOGIN_URL, reply));

      await signIn();

      expect(await screen.findByRole("alert")).toHaveTextContent(
        "Couldn't sign you in. Try again in a moment.",
      );
      expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
    },
  );
});

describe("LoginForm before the page is interactive", () => {
  // Until React hydrates, a submit is the browser's own form GET to /login, which puts
  // the email and the password in the address bar and in the server's access logs.
  it("can't send the password in a URL", () => {
    const page = document.createElement("div");
    page.innerHTML = renderToString(<LoginForm />);

    expect(page.querySelector("form")).toHaveAttribute("method", "post");
    expect(
      within(page).getByRole("button", { name: "Sign in" }),
    ).toBeDisabled();
  });
});
