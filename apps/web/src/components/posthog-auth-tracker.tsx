"use client";

import type { User } from "@supabase/supabase-js";
import { useEffect, useRef, useState, type ReactNode } from "react";

import {
  capturePostHogEvent,
  identifyPostHogUser,
  resetPostHogUser,
} from "@/lib/posthog/client";
import { POSTHOG_EVENT } from "@/lib/posthog/events";
import { createClient } from "@/lib/supabase/client";
import { hasSupabaseAuthConfig } from "@/lib/supabase/config";

function resolveDisplayName(user: User): string | null {
  const fullName = typeof user.user_metadata?.full_name === "string"
    ? user.user_metadata.full_name.trim()
    : "";
  if (fullName) {
    return fullName;
  }

  const name = typeof user.user_metadata?.name === "string"
    ? user.user_metadata.name.trim()
    : "";
  if (name) {
    return name;
  }

  const emailPrefix = user.email?.split("@", 1)[0]?.trim();
  return emailPrefix || null;
}

function resolveAuthProvider(user: User): string {
  const provider = user.app_metadata?.provider;
  return typeof provider === "string" && provider.trim() ? provider : "supabase";
}

export function PostHogAuthTracker({ children }: { children: ReactNode }) {
  const [supabase] = useState(() => (
    hasSupabaseAuthConfig() ? createClient() : null
  ));
  const previousUserIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!supabase) {
      return;
    }

    let isActive = true;

    function syncUser(user: User | null) {
      if (user) {
        identifyPostHogUser({
          authProvider: resolveAuthProvider(user),
          email: user.email ?? null,
          id: user.id,
          name: resolveDisplayName(user),
        });
      } else if (previousUserIdRef.current) {
        resetPostHogUser();
      }

      previousUserIdRef.current = user?.id ?? null;
    }

    void supabase.auth.getUser().then(({ data }) => {
      if (!isActive) {
        return;
      }

      syncUser(data.user ?? null);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (!isActive) {
        return;
      }

      const previousUserId = previousUserIdRef.current;
      const nextUser = session?.user ?? null;

      syncUser(nextUser);

      if (event === "SIGNED_IN" && nextUser && previousUserId !== nextUser.id) {
        capturePostHogEvent(POSTHOG_EVENT.UserAuthenticated, {
          auth_provider: resolveAuthProvider(nextUser),
          has_verified_email: Boolean(nextUser.email_confirmed_at),
        });
      }
    });

    return () => {
      isActive = false;
      subscription.unsubscribe();
    };
  }, [supabase]);

  return <>{children}</>;
}
