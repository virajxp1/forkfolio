import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  createClientMock,
  getUserMock,
  hasSupabaseAuthConfigMock,
  onAuthStateChangeMock,
  signInWithOAuthMock,
  signOutMock,
  unsubscribeMock,
} = vi.hoisted(() => {
  const getUserMock = vi.fn();
  const unsubscribeMock = vi.fn();
  const onAuthStateChangeMock = vi.fn(() => ({
    data: {
      subscription: {
        unsubscribe: unsubscribeMock,
      },
    },
  }));
  const signInWithOAuthMock = vi.fn();
  const signOutMock = vi.fn();
  const createClientMock = vi.fn(() => ({
    auth: {
      getUser: getUserMock,
      onAuthStateChange: onAuthStateChangeMock,
      signInWithOAuth: signInWithOAuthMock,
      signOut: signOutMock,
    },
  }));
  const hasSupabaseAuthConfigMock = vi.fn();

  return {
    createClientMock,
    getUserMock,
    hasSupabaseAuthConfigMock,
    onAuthStateChangeMock,
    signInWithOAuthMock,
    signOutMock,
    unsubscribeMock,
  };
});

vi.mock("@/lib/supabase/client", () => ({
  createClient: createClientMock,
}));

vi.mock("@/lib/supabase/config", () => ({
  hasSupabaseAuthConfig: hasSupabaseAuthConfigMock,
}));

import { AuthProfileButton } from "./auth-profile-button";

describe("AuthProfileButton", () => {
  beforeEach(() => {
    createClientMock.mockClear();
    getUserMock.mockReset();
    hasSupabaseAuthConfigMock.mockReset();
    onAuthStateChangeMock.mockClear();
    signInWithOAuthMock.mockReset();
    signOutMock.mockReset();
    unsubscribeMock.mockClear();

    hasSupabaseAuthConfigMock.mockReturnValue(true);
    signInWithOAuthMock.mockResolvedValue({ error: null });
    signOutMock.mockResolvedValue({ error: null });
  });

  it("treats a missing auth session as a signed-out state instead of an error", async () => {
    getUserMock.mockResolvedValue({
      data: { user: null },
      error: { message: "Auth session missing!" },
    });

    render(<AuthProfileButton />);

    expect(await screen.findByRole("button", { name: /Sign In/i })).toBeInTheDocument();
    expect(screen.queryByText("Auth session missing!")).not.toBeInTheDocument();
  });

  it("still shows unexpected auth errors", async () => {
    getUserMock.mockResolvedValue({
      data: { user: null },
      error: { message: "Failed to reach auth service." },
    });

    render(<AuthProfileButton />);

    expect(await screen.findByRole("button", { name: /Sign In/i })).toBeInTheDocument();
    expect(await screen.findByText("Failed to reach auth service.")).toBeInTheDocument();
  });
});
