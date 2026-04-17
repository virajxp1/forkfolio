import { NextResponse } from "next/server";

import { hasSupabaseAuthConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

function resolveRedirectOrigin(requestUrl: URL): string {
  const configuredAppOrigin = process.env.FORKFOLIO_APP_ORIGIN?.trim();
  if (!configuredAppOrigin) {
    return requestUrl.origin;
  }

  try {
    return new URL(configuredAppOrigin).origin;
  } catch {
    return requestUrl.origin;
  }
}

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const { searchParams } = requestUrl;
  const origin = resolveRedirectOrigin(requestUrl);
  const code = searchParams.get("code");
  let next = searchParams.get("next") ?? "/";

  if (!next.startsWith("/")) {
    next = "/";
  }

  if (!hasSupabaseAuthConfig()) {
    return NextResponse.redirect(`${origin}/auth/auth-code-error`);
  }

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);

    if (!error) {
      return NextResponse.redirect(`${origin}${next}`);
    }
  }

  return NextResponse.redirect(`${origin}/auth/auth-code-error`);
}
