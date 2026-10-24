// @vitest-environment node
import { delay, http, HttpResponse } from "msw";
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

  it("reports unreachable when health answers with an error status", async () => {
    server.use(
      http.get(HEALTH_URL, () =>
        HttpResponse.json({ status: "degraded", db: "error" }, { status: 503 }),
      ),
    );

    const health = await getApiHealth(API_ORIGIN);

    expect(health).toBe("unreachable");
  });

  it("reports unreachable when the API cannot be reached at all", async () => {
    server.use(http.get(HEALTH_URL, () => HttpResponse.error()));

    const health = await getApiHealth(API_ORIGIN);

    expect(health).toBe("unreachable");
  });

  it("reports unreachable when the API does not answer in time", async () => {
    server.use(
      http.get(HEALTH_URL, async () => {
        await delay(200);
        return HttpResponse.json({ status: "ok", db: "ok", version: "1.0.0" });
      }),
    );

    const health = await getApiHealth(API_ORIGIN, { timeoutMs: 20 });

    expect(health).toBe("unreachable");
  });
});
