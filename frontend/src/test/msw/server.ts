import { setupServer } from "msw/node";

// No default handlers: each test declares the API responses it needs with `server.use(...)`.
// Any request without a handler fails the test (see `onUnhandledRequest` in ../setup.ts).
export const server = setupServer();
