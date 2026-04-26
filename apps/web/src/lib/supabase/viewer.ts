import "server-only";

import { hasSupabaseAuthConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

export type RequiredViewerUserIdResult =
  | {
      viewerUserId: string;
      detail?: never;
      status?: never;
    }
  | {
      viewerUserId: null;
      detail: string;
      status: 401 | 503;
    };

export async function getOptionalViewerUserId(): Promise<string | null> {
  if (!hasSupabaseAuthConfig()) {
    return null;
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) {
    return null;
  }

  return data.user.id;
}

export async function getRequiredViewerUserId(
  featureName: string,
  signedOutDetail = "Sign in to continue.",
): Promise<RequiredViewerUserIdResult> {
  if (!hasSupabaseAuthConfig()) {
    return {
      viewerUserId: null,
      detail: `${featureName} require Supabase Auth configuration.`,
      status: 503,
    };
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) {
    return {
      viewerUserId: null,
      detail: signedOutDetail,
      status: 401,
    };
  }

  return { viewerUserId: data.user.id };
}
