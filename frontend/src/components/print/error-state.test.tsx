import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ErrorState } from "./index";

const refresh = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ refresh }) }));

describe("ErrorState", () => {
  it("shows the problem's title, detail and request id", () => {
    render(
      <ErrorState
        title="Service unavailable"
        detail="The database is not reachable."
        requestId="6f1c2b9e"
      />,
    );

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Service unavailable");
    expect(alert).toHaveTextContent("The database is not reachable.");
    expect(alert).toHaveTextContent("Request ID: 6f1c2b9e");
  });

  it("tries again with the retry it is given", async () => {
    const onRetry = vi.fn();
    render(<ErrorState title="Something went wrong" onRetry={onRetry} />);

    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(onRetry).toHaveBeenCalledOnce();
    expect(refresh).not.toHaveBeenCalled();
  });

  it("reloads the page's data when it has no retry of its own", async () => {
    render(<ErrorState title="Something went wrong" />);

    await userEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(refresh).toHaveBeenCalledOnce();
  });
});
