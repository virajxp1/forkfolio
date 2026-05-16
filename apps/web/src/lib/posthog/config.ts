export type PostHogViewerState = "anonymous" | "authenticated";

const posthogToken = "phc_ApXgcUDQgbUF7oFBWW3d2DtFbFvHKeE3estJyaoxcLVS";
const posthogHost = "https://us.i.posthog.com";
const posthogAppName = "forkfolio-web";
const posthogAppNamespace = "forkfolio";

function getDeploymentEnvironment(): string {
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname.trim().toLowerCase();

    if (!hostname || hostname === "localhost" || hostname === "127.0.0.1") {
      return "local";
    }

    if (hostname.includes("staging")) {
      return "staging";
    }

    return "production";
  }

  return process.env.NODE_ENV?.trim() || "development";
}

export function hasPostHogConfig(): boolean {
  return Boolean(posthogToken);
}

export function getPostHogPublicConfig() {
  return {
    token: posthogToken,
    host: posthogHost,
  };
}

export function getPostHogAppProperties() {
  return {
    app_name: posthogAppName,
    app_namespace: posthogAppNamespace,
    app_platform: "web" as const,
    deployment_environment: getDeploymentEnvironment(),
  };
}

export function getPostHogAppName(): string {
  return posthogAppName;
}
