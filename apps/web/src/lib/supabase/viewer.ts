import "server-only";

import { hasSupabaseAuthConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

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
