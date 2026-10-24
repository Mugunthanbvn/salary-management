import type { NextConfig } from "next";

import { API_ORIGIN } from "./src/lib/api/origin";

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
  // Insights is the landing page (docs/13-frontend-ux.md §2).
  async redirects() {
    return [{ source: "/", destination: "/insights", permanent: false }];
  },
  // The only proxying in Next.js: the browser calls /api/... on this origin and Next.js
  // forwards it unchanged to FastAPI (docs/17-deployment.md §3.4).
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/api/:path*` }];
  },
};

export default nextConfig;
