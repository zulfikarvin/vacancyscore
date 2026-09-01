import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_API_URL?.replace(/\/$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (!backendUrl) return [];
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
