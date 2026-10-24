// @vitest-environment node
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { server } from "@/test/msw/server";

import { getApiHealth } from "./health";

const API_ORIGIN = "http://api.test";
const HEALTH_URL = `${API_ORIGIN}/api/v1/health`;

describe("getApiHealth", () => {
  it("reports ok when the health endpoint answers 200", async () => {
    server.use(
      http.get(HEALTH_URL, () =>
        HttpResponse.json({ status: "ok", db: "ok", version: "1.0.0" }),
      ),
    );

    const health = await getApiHealth(API_ORIGIN);

    expect(health).toBe("ok");
  });
});
