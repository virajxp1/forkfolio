import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import nextEnv from "@next/env";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const webDir = path.resolve(scriptDir, "..");
const repoRootDir = path.resolve(webDir, "..", "..");
const { loadEnvConfig } = nextEnv;

loadEnvConfig(repoRootDir, process.env.NODE_ENV !== "production");

const [, , command, ...args] = process.argv;
if (!command) {
  console.error("Missing command. Usage: node scripts/run-with-root-env.mjs <cmd> [...args]");
  process.exit(1);
}

const child = spawn(command, args, {
  cwd: webDir,
  env: process.env,
  stdio: "inherit",
  shell: process.platform === "win32",
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});

child.on("error", (error) => {
  console.error(`Failed to run command: ${error.message}`);
  process.exit(1);
});
