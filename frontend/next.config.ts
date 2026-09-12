import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output for the Docker image (see frontend/Dockerfile) — bundles
  // only the production dependencies actually traced from the build instead
  // of shipping the whole workspace node_modules.
  output: "standalone",
  // This app lives in a pnpm workspace (../pnpm-lock.yaml at the repo root);
  // without this, file tracing anchors at `frontend/` and misses workspace
  // node_modules, producing an incomplete standalone bundle.
  outputFileTracingRoot: path.join(__dirname, ".."),
};

export default nextConfig;
