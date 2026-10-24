import type { NextConfig } from "next";

const API_ORIGIN = process.env.API_ORIGIN;

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  // The only proxying in Next.js: the browser calls /api/... on this origin and Next.js
  // forwards it unchanged to FastAPI (docs/17-deployment.md §3.4).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
