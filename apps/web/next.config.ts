import type { NextConfig } from "next";
import { loadEnvConfig } from "@next/env";
import path from "node:path";
import { fileURLToPath } from "node:url";

const webAppDir = path.dirname(fileURLToPath(import.meta.url));
const repoRootDir = path.resolve(webAppDir, "../..");

// Load repo-level .env files so this app can be configured from the monorepo root.
loadEnvConfig(repoRootDir, process.env.NODE_ENV !== "production");

const nextConfig: NextConfig = {
  /* config options here */
};

export default nextConfig;
