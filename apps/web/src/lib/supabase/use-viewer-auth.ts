"use client";

import type { User } from "@supabase/supabase-js";
import { useEffect, useRef, useState } from "react";

import { isExpectedSignedOutMessage } from "@/lib/supabase/auth";
import { createClient as createSupabaseClient } from "@/lib/supabase/client";
import { hasSupabaseAuthConfig } from "@/lib/supabase/config";

export type ViewerAuth =
  | { status: "resolving" }
  | { status: "ready"; viewerUserId: string }
  | {
      status: "blocked";
      reason: "auth_required" | "auth_unavailable";
      error: string | null;
    };

export type ViewerAccessSeed =
  | { accessState: "ready"; viewerUserId: string; errorMessage: null }
  | {
      accessState: "auth_required" | "auth_unavailable";
      viewerUserId: null;
      errorMessage: string | null;
    };

type ViewerBlockedReason = Extract<ViewerAuth, { status: "blocked" }>["reason"];

function blockedAuth(reason: ViewerBlockedReason, error: string | null = null): ViewerAuth {
  return { status: "blocked", reason, error };
}

function seedToAuth(seed: ViewerAccessSeed | null | undefined): ViewerAuth {
  if (!seed) {
    return hasSupabaseAuthConfig() ? { status: "resolving" } : blockedAuth("auth_unavailable");
  }
  if (seed.accessState === "ready") {
    return { status: "ready", viewerUserId: seed.viewerUserId };
  }
  return blockedAuth(seed.accessState, seed.errorMessage);
}

function userIdOf(user: User | null | undefined): string | null {
  return user?.id?.trim() || null;
}

export function useViewerAuth(initialAccess?: ViewerAccessSeed | null) {
  const [supabase] = useState(() => (hasSupabaseAuthConfig() ? createSupabaseClient() : null));
  const [auth, setAuth] = useState<ViewerAuth>(() => seedToAuth(initialAccess));
  const viewerRef = useRef<string | null>(initialAccess?.viewerUserId ?? null);

  function commit(next: ViewerAuth) {
    viewerRef.current = next.status === "ready" ? next.viewerUserId : null;
    setAuth(next);
  }

  useEffect(() => {
    if (!supabase) {
      return;
    }

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      const userId = userIdOf(session?.user ?? null);
      if (userId) {
        if (viewerRef.current === userId) {
          setAuth((current) =>
            current.status === "ready" && current.viewerUserId === userId
              ? current
              : { status: "ready", viewerUserId: userId },
          );
          return;
        }
        commit({ status: "ready", viewerUserId: userId });
        return;
      }
      setAuth((current) => {
        if (current.status === "blocked" && current.reason === "auth_required" && !current.error) {
          viewerRef.current = null;
          return current;
        }
        viewerRef.current = null;
        return blockedAuth("auth_required");
      });
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [supabase]);

  function isViewerActive(activeViewerUserId: string | null): boolean {
    return Boolean(activeViewerUserId && viewerRef.current === activeViewerUserId);
  }

  function markBlocked(reason: ViewerBlockedReason, error: string | null = null) {
    commit(blockedAuth(reason, error));
  }

  async function retry() {
    if (!supabase) {
      commit(blockedAuth("auth_unavailable"));
      return;
    }
    commit({ status: "resolving" });
    try {
      const { data, error } = await supabase.auth.getUser();
      const userId = userIdOf(data.user);
      if (userId) {
        commit({ status: "ready", viewerUserId: userId });
        return;
      }
      if (error?.message && !isExpectedSignedOutMessage(error.message)) {
        commit(blockedAuth("auth_unavailable", error.message));
        return;
      }
      commit(blockedAuth("auth_required"));
    } catch (error) {
      const message =
        error instanceof Error && error.message ? error.message : "Failed to verify your account.";
      commit(blockedAuth("auth_unavailable", message));
    }
  }

  return { auth, isViewerActive, markBlocked, retry };
}
