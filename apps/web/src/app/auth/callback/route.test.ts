/** @vitest-environment node */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const {
  createClientMock,
  exchangeCodeForSessionMock,
  hasSupabaseAuthConfigMock,
} = vi.hoisted(() => {
  const exchangeCodeForSessionMock = vi.fn();
  const createClientMock = vi.fn(async () => ({
    auth: {
      exchangeCodeForSession: exchangeCodeForSessionMock,
    },
  }));
  const hasSupabaseAuthConfigMock = vi.fn();

  return {
    createClientMock,
    exchangeCodeForSessionMock,
    hasSupabaseAuthConfigMock,
  };
});

vi.mock("@/lib/supabase/server", () => ({
  createClient: createClientMock,
}));

vi.mock("@/lib/supabase/config", () => ({
  hasSupabaseAuthConfig: hasSupabaseAuthConfigMock,
}));

import { GET } from "./route";

const ORIGINAL_APP_ORIGIN = process.env.FORKFOLIO_APP_ORIGIN;

describe("/auth/callback route", () => {
  beforeEach(() => {
    createClientMock.mockClear();
    exchangeCodeForSessionMock.mockReset();
    hasSupabaseAuthConfigMock.mockReset();
    hasSupabaseAuthConfigMock.mockReturnValue(true);
    exchangeCodeForSessionMock.mockResolvedValue({ error: null });
    delete process.env.FORKFOLIO_APP_ORIGIN;
  });

  afterEach(() => {
    if (ORIGINAL_APP_ORIGIN === undefined) {
      delete process.env.FORKFOLIO_APP_ORIGIN;
      return;
    }
    process.env.FORKFOLIO_APP_ORIGIN = ORIGINAL_APP_ORIGIN;
  });

  it("redirects to auth error when Supabase Auth is not configured", async () => {
    hasSupabaseAuthConfigMock.mockReturnValue(false);

    const response = await GET(new Request("https://forkfolio.app/auth/callback?code=abc"));

    expect(response.headers.get("location")).toBe("https://forkfolio.app/auth/auth-code-error");
    expect(createClientMock).not.toHaveBeenCalled();
  });

  it("redirects to requested internal path after successful code exchange", async () => {
    const response = await GET(
      new Request("https://forkfolio.app/auth/callback?code=abc&next=/books"),
    );

    expect(exchangeCodeForSessionMock).toHaveBeenCalledWith("abc");
    expect(response.headers.get("location")).toBe("https://forkfolio.app/books");
  });

  it("sanitizes external next values to root", async () => {
    const response = await GET(
      new Request("https://forkfolio.app/auth/callback?code=abc&next=https://evil.example/phish"),
    );

    expect(response.headers.get("location")).toBe("https://forkfolio.app/");
  });

  it("uses forwarded host and proto when request origin is an internal proxy URL", async () => {
    const response = await GET(
      new Request("http://localhost:10000/auth/callback?code=abc&next=/bag", {
        headers: {
          "x-forwarded-host": "forkfolio-fe.onrender.com",
          "x-forwarded-proto": "https",
        },
      }),
    );

    expect(response.headers.get("location")).toBe("https://forkfolio-fe.onrender.com/bag");
  });

  it("uses configured app origin and ignores x-forwarded-host", async () => {
    process.env.FORKFOLIO_APP_ORIGIN = "https://www.forkfolio.app/account";

    const response = await GET(
      new Request("https://internal-host.local/auth/callback?code=abc&next=/bag", {
        headers: {
          "x-forwarded-host": "evil.example",
        },
      }),
    );

    expect(response.headers.get("location")).toBe("https://www.forkfolio.app/bag");
  });

  it("falls back to request origin when configured app origin is invalid", async () => {
    process.env.FORKFOLIO_APP_ORIGIN = "not-a-url";

    const response = await GET(
      new Request("https://internal-host.local/auth/callback?code=abc&next=/bag"),
    );

    expect(response.headers.get("location")).toBe("https://internal-host.local/bag");
  });

  it("redirects to auth error when code exchange fails", async () => {
    exchangeCodeForSessionMock.mockResolvedValue({
      error: { message: "expired code" },
    });

    const response = await GET(
      new Request("https://forkfolio.app/auth/callback?code=expired-code&next=/books"),
    );

    expect(response.headers.get("location")).toBe("https://forkfolio.app/auth/auth-code-error");
  });
});
