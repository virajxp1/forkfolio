import { createBrowserClient } from "@supabase/ssr";

import { getSupabasePublicConfig } from "@/lib/supabase/config";

export function createClient() {
  const { supabaseUrl, supabasePublishableKey } = getSupabasePublicConfig();
  return createBrowserClient(supabaseUrl, supabasePublishableKey);
}
