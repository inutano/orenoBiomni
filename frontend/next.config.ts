import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    const backend = process.env.BACKEND_URL || "http://backend:8000";
    return [
      { source: "/api/:path*", destination: `${backend}/api/:path*` },
      { source: "/ga4gh/:path*", destination: `${backend}/ga4gh/:path*` },
    ];
  },
};

export default nextConfig;
