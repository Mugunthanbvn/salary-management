import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PageTitle, Section } from "./index";

describe("PageTitle", () => {
  it("is the page's heading, with its summary sentence under it", () => {
    render(
      <PageTitle title="How ACME pays people">
        9,012 employees in 10 countries.
      </PageTitle>,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "How ACME pays people" }),
    ).toBeVisible();
    expect(screen.getByText("9,012 employees in 10 countries.")).toBeVisible();
  });
});

describe("Section", () => {
  it("is a region named by the question it answers", () => {
    render(
      <Section question="Is anyone paid unfairly?">
        <p>One team stands out.</p>
      </Section>,
    );

    const region = screen.getByRole("region", {
      name: "Is anyone paid unfairly?",
    });
    expect(region).toHaveTextContent("One team stands out.");
  });
});
