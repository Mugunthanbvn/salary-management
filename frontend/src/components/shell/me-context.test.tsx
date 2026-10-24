import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeMe, VIEWER_PERMISSIONS } from "@/test/fixtures";

import { MeProvider, useMe } from "./me-context";

function ImportHint() {
  const me = useMe();
  return (
    <p>
      {me.user.full_name} {me.can("IMPORT") ? "can import" : "cannot import"}
    </p>
  );
}

describe("useMe", () => {
  it.each([
    { permissions: undefined, text: "Hema Iyer can import" },
    { permissions: VIEWER_PERMISSIONS, text: "Hema Iyer cannot import" },
  ])(
    "gives client components the person and can(): $text",
    ({ permissions, text }) => {
      const me = permissions ? makeMe({ permissions }) : makeMe();

      render(
        <MeProvider me={me}>
          <ImportHint />
        </MeProvider>,
      );

      expect(screen.getByText(text)).toBeVisible();
    },
  );
});
