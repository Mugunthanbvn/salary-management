import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Me } from "@/lib/permissions";
import { makeMe } from "@/test/fixtures";
import { renderInApp } from "@/test/render";

import ImportPage from "./page";

const { getMe } = vi.hoisted(() => ({ getMe: vi.fn<() => Promise<Me>>() }));
vi.mock("@/lib/api/me", () => ({ getMe }));

describe("/employees/import", () => {
  it("opens on the upload step, with the templates and the file picker", async () => {
    const me = makeMe();
    getMe.mockResolvedValue(me);

    renderInApp(await ImportPage(), { me });

    expect(
      await screen.findByRole("link", { name: "Download the CSV template" }),
    ).toBeVisible();
    expect(screen.getByLabelText(/Choose a file/)).toBeInTheDocument();
  });
});
