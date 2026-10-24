import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ApiStatus } from "./api-status";

describe("ApiStatus", () => {
  it("tells the user the API is ok when it is healthy", () => {
    render(<ApiStatus status="ok" />);

    expect(screen.getByRole("status")).toHaveTextContent("API: ok");
  });
});
