const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() ?? "";
const supabasePublishableKey =
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim() ?? "";

export function hasSupabaseAuthConfig(): boolean {
  return Boolean(supabaseUrl && supabasePublishableKey);
}

export function getSupabasePublicConfig() {
  if (!hasSupabaseAuthConfig()) {
    throw new Error(
      "Supabase Auth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.",
    );
  }

  return {
    supabaseUrl,
    supabasePublishableKey,
  };
}
