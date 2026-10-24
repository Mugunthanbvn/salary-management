import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiStatus } from "./api-status";

describe("ApiStatus", () => {
  it.each([
    { status: "ok", text: "API: ok" },
    { status: "unreachable", text: "API unreachable" },
  ] as const)("shows $text when the API is $status", ({ status, text }) => {
    render(<ApiStatus status={status} />);

    expect(screen.getByRole("status")).toHaveTextContent(text);
  });
});
