import path from "path";
import { fileURLToPath } from "url";
import type { NextConfig } from "next";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const exporting = process.env.NEXT_OUTPUT === "export";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  turbopack: {
    root: frontendRoot,
  },
  ...(exporting
    ? {
        output: "export",
        images: { unoptimized: true },
        trailingSlash: false,
      }
    : {
        async rewrites() {
          const backend = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
          return [
            {
              source: "/api/v1/:path*",
              destination: `${backend}/api/v1/:path*`,
            },
          ];
        },
      }),
};

export default nextConfig;
