import { api } from "@/lib/api/client";
import { toProblem } from "@/lib/api/problem";
import type { components } from "@/lib/api/schema";

export type AskResponse = components["schemas"]["AskResponse"];
export type ChatMessage = components["schemas"]["ChatMessage"];

/** docs/glossary.md §3: the same caps as the API. */
export const MAX_QUESTION_CHARS = 1000;
export const MAX_TURNS = 6;

export type AskResult =
  { ok: true; answer: AskResponse } | { ok: false; message: string };

/**
 * POST /api/v1/ask with a client fetch through the /api rewrite (the session cookie goes
 * with it). Not a Server Action: the answer is JSON for this page only, nothing to
 * revalidate, and a client fetch keeps the pending state and Retry-After in the browser.
 */
export async function askAboutPay(messages: ChatMessage[]): Promise<AskResult> {
  try {
    const { data, error, response } = await api.POST("/api/v1/ask", {
      body: { messages },
    });
    if (data) return { ok: true, answer: data };
    const problem = await toProblem(response, error);
    return {
      ok: false,
      message: errorMessage(problem.status, problem.detail, response),
    };
  } catch {
    return { ok: false, message: COULD_NOT_ANSWER };
  }
}

const COULD_NOT_ANSWER = "Couldn't get an answer. Try again.";

function errorMessage(
  status: number,
  detail: string | null,
  response: Response,
): string {
  if (status === 429) {
    // The detail says which limit: the hourly one, or the provider being busy.
    const reason = detail ?? "The assistant is busy.";
    return `${reason} ${tryAgainIn(response.headers.get("Retry-After"))}`;
  }
  if (status === 502) {
    return "The assistant is unavailable right now. Try again in a moment.";
  }
  if (status === 503) return "Ask is turned off on this deployment.";
  return COULD_NOT_ANSWER;
}

function tryAgainIn(retryAfter: string | null): string {
  const seconds = Number(retryAfter);
  if (!retryAfter || !Number.isFinite(seconds) || seconds <= 0) {
    return "Try again later.";
  }
  const minutes = Math.ceil(seconds / 60);
  return `Try again in ${minutes} ${minutes === 1 ? "minute" : "minutes"}.`;
}

/** The conversation to send: the last MAX_TURNS messages, ending with the new question. */
export function lastTurns(
  history: ChatMessage[],
  question: string,
): ChatMessage[] {
  return [...history, { role: "user" as const, content: question }].slice(
    -MAX_TURNS,
  );
}
