import posthog from "posthog-js";

import {
  getPostHogAppName,
  getPostHogAppProperties,
  getPostHogPublicConfig,
  hasPostHogConfig,
  type PostHogViewerState,
} from "@/lib/posthog/config";

type PostHogCaptureProperties = Record<
  string,
  string | number | boolean | null | undefined
>;

type IdentifyUserArgs = {
  authProvider?: string | null;
  email?: string | null;
  id: string;
  name?: string | null;
};

let hasInitializedPostHog = false;

function registerViewerContext(
  viewerState: PostHogViewerState,
  authenticatedUserId?: string,
): void {
  posthog.register({
    ...getPostHogAppProperties(),
    viewer_state: viewerState,
    ...(authenticatedUserId
      ? { authenticated_app_user_id: authenticatedUserId }
      : {}),
  });

  if (!authenticatedUserId) {
    posthog.unregister("authenticated_app_user_id");
  }
}

export function initPostHog(): void {
  if (typeof window === "undefined" || hasInitializedPostHog || !hasPostHogConfig()) {
    return;
  }

  const { token, host } = getPostHogPublicConfig();

  try {
    posthog.init(token, {
      api_host: host,
      autocapture: false,
      capture_pageleave: "if_capture_pageview",
      capture_pageview: "history_change",
      defaults: "2026-01-30",
      disable_session_recording: true,
      person_profiles: "identified_only",
      loaded: () => {
        registerViewerContext("anonymous");
      },
    });

    hasInitializedPostHog = true;
  } catch (error) {
    if (process.env.NODE_ENV !== "production") {
      console.error("PostHog initialization failed.", error);
    }
  }
}

export function capturePostHogEvent(
  eventName: string,
  properties?: PostHogCaptureProperties,
): void {
  if (!hasPostHogConfig()) {
    return;
  }

  posthog.capture(eventName, properties);
}

export function identifyPostHogUser({
  authProvider,
  email,
  id,
  name,
}: IdentifyUserArgs): void {
  if (!hasPostHogConfig()) {
    return;
  }

  posthog.identify(
    id,
    {
      auth_provider: authProvider ?? "supabase",
      email: email ?? undefined,
      name: name ?? undefined,
    },
    {
      first_seen_app: getPostHogAppName(),
    },
  );

  registerViewerContext("authenticated", id);
}

export function resetPostHogUser(): void {
  if (!hasPostHogConfig()) {
    return;
  }

  posthog.reset();
  registerViewerContext("anonymous");
}
