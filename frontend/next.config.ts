import type { NextConfig } from "next";

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
  // Local development only: the browser calls /api/... on this origin and Next.js forwards it
  // to uvicorn at API_ORIGIN. On Vercel, vercel.json routes /api to the backend service before
  // Next.js sees the request, so no proxy is added (docs/17-deployment.md §3.4).
  async rewrites() {
    const origin = process.env.API_ORIGIN;
    return origin
      ? [{ source: "/api/:path*", destination: `${origin}/api/:path*` }]
      : [];
  },
};

export default nextConfig;
