"use client";

import Link from "next/link";
import {
  Fragment,
  useId,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
} from "react";

import { Button } from "@/components/ui/button";
import { formatMoney } from "@/lib/money";
import { formatCount } from "@/lib/numbers";

import {
  askAboutPay,
  lastTurns,
  MAX_QUESTION_CHARS,
  type AskResponse,
  type ChatMessage,
} from "./ask-api";

type Exchange = {
  id: number;
  question: string;
  answer?: AskResponse;
  error?: string;
};

type Figure = AskResponse["figures"][number];
type ToolCall = AskResponse["tool_calls"][number];

const SUGGESTIONS = [
  "Which country pays L3 engineers the most (USD)?",
  "Are any teams paid below their band?",
  "What is the median total pay in Singapore?",
  "How much do we spend on Sales vs Engineering?",
];

/** What each tool did, in plain words, for "How I got this". */
const TOOL_STEPS: Record<string, string> = {
  get_pay_overview: "Looked up the pay overview",
  get_pay_by_group: "Looked up pay by group",
  compare_groups: "Compared two groups",
  get_pay_equity_outliers: "Checked pay against pay bands",
  get_top_earners: "Listed the highest-paid people",
  search_employees: "Searched employees",
  get_fx_rates: "Looked up exchange rates",
};

const COUNT = new Intl.NumberFormat("en-US");

/** A path on this site: one leading slash, never `//host` (protocol-relative). */
const SITE_PATH = /^\/(?!\/)/;

/**
 * The Ask conversation (docs/13-frontend-ux.md §4.8). History lives in this component's
 * state only and is never saved; each question sends the last 6 turns. Every figure, the
 * trace and the dashboard link come from the API: the page only formats them.
 */
export function AskChat() {
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState(false);
  const nextId = useRef(1);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const counterId = useId();

  async function send(question: string) {
    const text = question.trim();
    if (!text || pending) return;
    const history: ChatMessage[] = exchanges.flatMap((exchange) =>
      exchange.answer
        ? [
            { role: "user" as const, content: exchange.question },
            { role: "assistant" as const, content: exchange.answer.answer },
          ]
        : [],
    );
    const id = nextId.current++;
    setExchanges((current) => [...current, { id, question: text }]);
    setDraft("");
    setPending(true);
    const result = await askAboutPay(lastTurns(history, text));
    setExchanges((current) =>
      current.map((exchange) =>
        exchange.id !== id
          ? exchange
          : result.ok
            ? { ...exchange, answer: result.answer }
            : { ...exchange, error: result.message },
      ),
    );
    setPending(false);
    inputRef.current?.focus();
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(draft);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter adds a line. Not while an IME is composing a word.
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      void send(draft);
    }
  }

  return (
    <div className="flex min-h-[calc(100dvh-14rem)] flex-col sm:min-h-0">
      <div className="mt-5 flex flex-wrap gap-x-6 gap-y-1">
        {SUGGESTIONS.map((suggestion) => (
          <Button
            key={suggestion}
            type="button"
            variant="link"
            disabled={pending}
            onClick={() => void send(suggestion)}
            className="text-left text-[15px] whitespace-normal"
          >
            {suggestion}
          </Button>
        ))}
      </div>

      <div className="flex-1">
        {exchanges.map((exchange, index) => (
          <ExchangeView
            key={exchange.id}
            exchange={exchange}
            first={index === 0}
          />
        ))}
      </div>

      <form
        onSubmit={onSubmit}
        className="sticky bottom-[calc(3.5rem+env(safe-area-inset-bottom))] z-10 mt-8 bg-paper pt-3 pb-3 sm:static sm:mt-12 sm:pb-0"
      >
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <label htmlFor="ask-question" className="text-sm text-ink-2">
            Ask a question about pay
          </label>
          <span id={counterId} className="text-[13px] text-ink-3 tabular-nums">
            {COUNT.format(draft.length)} / {COUNT.format(MAX_QUESTION_CHARS)}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-end gap-3">
          <textarea
            id="ask-question"
            ref={inputRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            maxLength={MAX_QUESTION_CHARS}
            rows={1}
            aria-describedby={counterId}
            placeholder="For example: what is the median pay for L4 engineers in the UK?"
            className="[field-sizing:content] min-h-12 min-w-0 flex-[999_1_320px] resize-none border-0 border-b-2 border-ink bg-transparent py-3 font-serif text-[18px] leading-snug text-ink placeholder:text-ink-3 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-blue-pen sm:text-[20px]"
          />
          <Button
            type="submit"
            disabled={pending || !draft.trim()}
            className="min-h-12 flex-[1_0_auto] px-6"
          >
            Ask
          </Button>
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[13px] text-ink-3">
          <span>
            Questions aren&apos;t saved. Up to the last 6 turns are sent.
          </span>
          {exchanges.length > 0 ? (
            <Button
              type="button"
              variant="ghost"
              disabled={pending}
              onClick={() => setExchanges([])}
              className="text-sm"
            >
              New conversation
            </Button>
          ) : null}
        </div>
      </form>
    </div>
  );
}

function ExchangeView({
  exchange,
  first,
}: {
  exchange: Exchange;
  first: boolean;
}) {
  const { question, answer, error } = exchange;
  const done = answer !== undefined || error !== undefined;
  return (
    <article
      aria-label={done ? "Question and answer" : "Question in progress"}
      className={
        first
          ? "mt-8 border-t-2 border-ink pt-6 sm:mt-10 sm:pt-8"
          : "mt-8 border-t border-rule pt-6 sm:mt-10 sm:pt-8"
      }
    >
      <p className="text-sm text-ink-2">You asked</p>
      <h2 className="mt-1.5 font-serif text-[24px] leading-tight font-semibold break-words sm:text-[30px]">
        {question}
      </h2>
      {answer ? <AnswerView answer={answer} /> : null}
      {error ? (
        <p role="alert" className="mt-4 text-[15px] text-ink red-pen">
          {error}
        </p>
      ) : null}
      {!done ? (
        <p
          role="status"
          className="mt-4 font-serif text-[18px] text-ink-2 italic sm:text-[20px]"
        >
          Thinking…
        </p>
      ) : null}
    </article>
  );
}

function AnswerView({ answer }: { answer: AskResponse }) {
  return (
    <>
      <div className="mt-5 space-y-4 font-serif text-[18px] leading-relaxed break-words sm:text-[21px]">
        {paragraphs(answer.answer).map((paragraph, index) => (
          <p key={index} className="whitespace-pre-line">
            {withBold(paragraph)}
          </p>
        ))}
      </div>
      {answer.figures.length > 0 ? (
        <dl className="mt-6 flex flex-wrap gap-x-10 gap-y-4">
          {answer.figures.map((figure, index) => (
            <div key={index} className="min-w-0">
              <dt className="text-[13px] text-ink-2">{figure.label}</dt>
              <dd className="mt-1 font-serif text-[24px] font-semibold whitespace-nowrap tabular-nums sm:text-[28px]">
                {figureValue(figure)}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      {answer.caveats.length > 0 ? (
        <ul className="mt-5 space-y-1 text-sm text-ink-2">
          {answer.caveats.map((caveat) => (
            <li key={caveat}>{caveat}</li>
          ))}
        </ul>
      ) : null}
      {answer.tool_calls.length > 0 ? (
        <details className="mt-4 text-[15px]">
          <summary className="flex min-h-11 cursor-pointer items-center font-bold">
            How I got this
          </summary>
          <ol
            aria-label="Steps"
            className="mt-2 list-decimal space-y-1 pl-5 text-ink-2"
          >
            {answer.tool_calls.map((call, index) => (
              <li key={index}>{stepText(call)}</li>
            ))}
          </ol>
        </details>
      ) : null}
      {answer.dashboard_link && SITE_PATH.test(answer.dashboard_link) ? (
        <Link
          href={answer.dashboard_link}
          className="mt-1 inline-flex min-h-11 items-center text-[15px] font-bold"
        >
          View in dashboard
        </Link>
      ) : null}
    </>
  );
}

function figureValue(figure: Figure): string {
  if (figure.value) {
    return formatMoney(figure.value.amount_minor, figure.value.currency);
  }
  const number = figure.number ?? "";
  // A count reads with thousands separators; a ratio stays as the tool returned it.
  return /^\d+$/.test(number) ? formatCount(Number(number)) : number;
}

function stepText(call: ToolCall): string {
  const step = TOOL_STEPS[call.name] ?? call.name;
  const args = describeArgs(call.args);
  const outcome = call.summary ? `: ${call.summary}` : "";
  return `${step}${args ? ` (${args})` : ""}${outcome}`;
}

/** `{filters: {country: "DE"}}` → "country DE"; compare_groups' a and b keep their names. */
function describeArgs(args: Record<string, unknown>): string {
  return Object.entries(args)
    .flatMap(([key, value]) => {
      if (value === null || value === undefined) return [];
      if (Array.isArray(value)) return [`${key} ${value.join(", ")}`];
      if (typeof value === "object") {
        const inner = describeArgs(value as Record<string, unknown>);
        if (!inner) return [];
        return [key === "filters" ? inner : `${key}: ${inner}`];
      }
      return [
        `${key} ${typeof value === "string" ? value : JSON.stringify(value)}`,
      ];
    })
    .join(" · ");
}

function paragraphs(markdown: string): string[] {
  return markdown
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean);
}

/** Markdown **bold** as <strong>; everything else stays text (React escapes it). */
function withBold(text: string): ReactNode {
  return text
    .split(/\*\*(.+?)\*\*/g)
    .map((part, index) =>
      index % 2 === 1 ? (
        <strong key={index}>{part}</strong>
      ) : (
        <Fragment key={index}>{part}</Fragment>
      ),
    );
}
