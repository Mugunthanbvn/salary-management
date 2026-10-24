import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { components } from "@/lib/api/schema";
import { server } from "@/test/msw/server";

import { AskChat } from "./ask-chat";

type AskRequest = components["schemas"]["AskRequest"];
type AskResponse = components["schemas"]["AskResponse"];
type Problem = components["schemas"]["Problem"];

const ASK_URL = "/api/v1/ask";

function makeAnswer(overrides: Partial<AskResponse> = {}): AskResponse {
  return {
    answer: "Customer Success in Germany is paid **below** its band.",
    figures: [
      {
        label: "Customer Success median base",
        value: { amount_minor: 4_800_000, currency: "EUR" },
        number: null,
      },
      {
        label: "Customer Success median compa-ratio",
        value: null,
        number: "0.93",
      },
    ],
    tool_calls: [
      {
        name: "get_pay_equity_outliers",
        args: { filters: { country: "DE" } },
        ok: true,
        summary: "104 below band, 70 above band",
        duration_ms: 12,
      },
    ],
    caveats: ["Full-time employees only"],
    dashboard_link: "/insights/pay-equity?country=DE",
    ...overrides,
  };
}

function problem(status: number, slug: string, detail: string): Problem {
  return {
    type: `https://acme.example/problems/${slug}`,
    title: slug,
    status,
    detail,
    instance: ASK_URL,
    request_id: "req-1",
  };
}

function answering(response: AskResponse = makeAnswer()) {
  const sent: AskRequest[] = [];
  server.use(
    http.post<never, AskRequest, AskResponse>(ASK_URL, async ({ request }) => {
      sent.push(await request.json());
      return HttpResponse.json(response);
    }),
  );
  return sent;
}

function failing(status: number, slug: string, detail: string, headers = {}) {
  server.use(
    http.post<never, AskRequest, Problem>(ASK_URL, () =>
      HttpResponse.json(problem(status, slug, detail), {
        status,
        headers: { "Content-Type": "application/problem+json", ...headers },
      }),
    ),
  );
}

async function ask(question = "Are we underpaying anyone in Germany?") {
  const box = screen.getByLabelText("Ask a question about pay");
  await userEvent.clear(box);
  await userEvent.type(box, question);
  await userEvent.click(screen.getByRole("button", { name: "Ask" }));
}

describe("AskChat", () => {
  it("shows that it is working while the answer is on its way", async () => {
    server.use(
      http.post(ASK_URL, async () => {
        await delay("infinite");
        return HttpResponse.json(makeAnswer());
      }),
    );
    render(<AskChat />);

    await ask();

    expect(await screen.findByRole("status")).toHaveTextContent("Thinking…");
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
    expect(
      screen.getByRole("heading", {
        name: "Are we underpaying anyone in Germany?",
      }),
    ).toBeVisible();
  });

  it("renders the answer with its figures, caveats and a link to the dashboard", async () => {
    answering();
    render(<AskChat />);

    await ask();

    const answer = await screen.findByRole("article", {
      name: "Question and answer",
    });
    expect(within(answer).getByText("below")).toHaveProperty(
      "tagName",
      "STRONG",
    );
    expect(within(answer).getByText("€48,000")).toBeVisible();
    expect(within(answer).getByText("0.93")).toBeVisible();
    expect(within(answer).getByText("Full-time employees only")).toBeVisible();
    expect(
      within(answer).getByRole("link", { name: "View in dashboard" }),
    ).toHaveAttribute("href", "/insights/pay-equity?country=DE");
  });

  it('explains "How I got this" from the tool calls', async () => {
    answering();
    render(<AskChat />);

    await ask();

    const how = await screen.findByText("How I got this");
    await userEvent.click(how);
    const steps = screen.getByRole("list", { name: "Steps" });
    expect(
      within(steps).getByText(/Checked pay against pay bands/),
    ).toBeVisible();
    expect(within(steps).getByText(/country DE/)).toBeVisible();
    expect(
      within(steps).getByText(/104 below band, 70 above band/),
    ).toBeVisible();
  });

  it("shows no dashboard link when the answer has none", async () => {
    answering(makeAnswer({ dashboard_link: null, tool_calls: [] }));
    render(<AskChat />);

    await ask();

    await screen.findByRole("article", { name: "Question and answer" });
    expect(
      screen.queryByRole("link", { name: "View in dashboard" }),
    ).toBeNull();
    expect(screen.queryByText("How I got this")).toBeNull();
  });

  it("says how many minutes to wait when rate limited", async () => {
    failing(
      429,
      "rate-limited",
      "You have asked 20 questions in the last hour.",
      {
        "Retry-After": "2460",
      },
    );
    render(<AskChat />);

    await ask();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You have asked 20 questions in the last hour. Try again in 41 minutes.",
    );
  });

  it("says the assistant is unavailable on a 502", async () => {
    failing(502, "upstream-unavailable", "The provider failed.");
    render(<AskChat />);

    await ask();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The assistant is unavailable right now. Try again in a moment.",
    );
  });

  it("says Ask is turned off on a 503", async () => {
    failing(503, "feature-disabled", "No LLM_API_KEY.");
    render(<AskChat />);

    await ask();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Ask is turned off on this deployment.",
    );
  });

  it("sends at most the last 6 turns, ending with the new question", async () => {
    const sent = answering(makeAnswer({ answer: "An answer." }));
    render(<AskChat />);

    for (const question of ["Q1", "Q2", "Q3", "Q4"]) {
      await ask(question);
      await waitFor(() =>
        expect(screen.getAllByRole("article")).toHaveLength(
          Number(question.slice(1)),
        ),
      );
    }

    const last = sent.at(-1)?.messages ?? [];
    expect(last).toHaveLength(6);
    expect(last.at(-1)).toEqual({ role: "user", content: "Q4" });
    expect(last.map((message) => message.role)).toEqual([
      "assistant",
      "user",
      "assistant",
      "user",
      "assistant",
      "user",
    ]);
  });

  it("caps a question at 1,000 characters and counts them", async () => {
    render(<AskChat />);

    const box = screen.getByLabelText("Ask a question about pay");
    await userEvent.type(box, "Median pay?");

    expect(box).toHaveAttribute("maxLength", "1000");
    expect(screen.getByText("11 / 1,000")).toBeVisible();
  });

  it("sends a suggested question", async () => {
    const sent = answering();
    render(<AskChat />);

    await userEvent.click(
      screen.getByRole("button", {
        name: "Are any teams paid below their band?",
      }),
    );

    await screen.findByRole("article", { name: "Question and answer" });
    expect(sent[0]?.messages).toEqual([
      { role: "user", content: "Are any teams paid below their band?" },
    ]);
  });

  it("starts a new conversation", async () => {
    answering();
    render(<AskChat />);
    await ask();
    await screen.findByRole("article", { name: "Question and answer" });

    await userEvent.click(
      screen.getByRole("button", { name: "New conversation" }),
    );

    expect(screen.queryByRole("article")).toBeNull();
  });
});
