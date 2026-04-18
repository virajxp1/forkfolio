import { NextResponse } from "next/server";

import { hasSupabaseAuthConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";

function getFirstHeaderValue(request: Request, headerName: string): string | null {
  const rawValue = request.headers.get(headerName)?.trim() ?? "";
  if (!rawValue) {
    return null;
  }

  const firstValue = rawValue.split(",", 1)[0]?.trim() ?? "";
  return firstValue || null;
}

function isLocalHost(host: string): boolean {
  return (
    host.startsWith("localhost") ||
    host.startsWith("127.0.0.1") ||
    host.startsWith("[::1]")
  );
}

function buildOrigin(protocol: string, host: string): string | null {
  try {
    return new URL(`${protocol}://${host}`).origin;
  } catch {
    return null;
  }
}

function resolveProxyOrigin(request: Request, requestUrl: URL): string | null {
  const forwardedHost = getFirstHeaderValue(request, "x-forwarded-host");
  const forwardedProto = getFirstHeaderValue(request, "x-forwarded-proto");
  const requestProtocol = requestUrl.protocol.replace(/:$/, "");

  if (forwardedHost) {
    const protocol = forwardedProto || (isLocalHost(forwardedHost) ? "http" : "https");
    return buildOrigin(protocol, forwardedHost);
  }

  const host = getFirstHeaderValue(request, "host");
  if (!host) {
    return null;
  }

  const protocol = forwardedProto ||
    (isLocalHost(host) || requestProtocol === "http" ? "http" : "https");
  return buildOrigin(protocol, host);
}

function resolveRedirectOrigin(request: Request): string {
  const requestUrl = new URL(request.url);
  const configuredAppOrigin = process.env.FORKFOLIO_APP_ORIGIN?.trim();
  if (!configuredAppOrigin) {
    return resolveProxyOrigin(request, requestUrl) ?? requestUrl.origin;
  }

  try {
    return new URL(configuredAppOrigin).origin;
  } catch {
    return resolveProxyOrigin(request, requestUrl) ?? requestUrl.origin;
  }
}

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const { searchParams } = requestUrl;
  const origin = resolveRedirectOrigin(request);
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
