import { File as NodeFile } from "node:buffer";

import { vi } from "vitest";

/**
 * For tests that upload a file through fetch. Vitest 4.1 turns a jsdom FormData body into
 * Node's by reading jsdom's Blob internals, which jsdom 30 no longer has, so the request
 * throws before MSW sees it. Node's own FormData and File go to Node's fetch untouched.
 * Call it in `beforeEach`, and `vi.unstubAllGlobals()` in `afterEach`.
 */
export async function useNodeFormData(): Promise<void> {
  // Node's FormData constructor, which the jsdom environment hides behind its own.
  const body = new URLSearchParams("a=1");
  const NodeFormData = (await new Response(body).formData()).constructor;
  vi.stubGlobal("FormData", NodeFormData);
}

/** A file as the browser's file picker hands it over. */
export function makeFile(name: string, content: string, type = ""): File {
  return new NodeFile([content], name, { type }) as unknown as File;
}
