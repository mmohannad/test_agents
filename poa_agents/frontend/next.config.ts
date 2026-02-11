import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // Allow longer API route execution for agent calls
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },
};

export default nextConfig;
