import { vi } from "vitest";

type SessionUser = { id: string };
export type Session = { user: SessionUser } | null;
type Listener = (event: string, session: Session) => void;

function createSupabaseMockHarness() {
  const listeners = new Set<Listener>();
  let currentSession: Session = null;

  const getUserMock = vi.fn();
  const signInWithOAuthMock = vi.fn();
  const signOutMock = vi.fn();
  const unsubscribeMock = vi.fn();

  const onAuthStateChangeMock = vi.fn((listener: Listener) => {
    listeners.add(listener);
    const sessionAtSubscribe = currentSession;
    queueMicrotask(() => {
      if (listeners.has(listener)) {
        listener("INITIAL_SESSION", sessionAtSubscribe);
      }
    });
    return {
      data: {
        subscription: {
          unsubscribe() {
            listeners.delete(listener);
            unsubscribeMock();
          },
        },
      },
    };
  });

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
    hasSupabaseAuthConfigMock,
    getUserMock,
    onAuthStateChangeMock,
    signInWithOAuthMock,
    signOutMock,
    unsubscribeMock,
    setSession(session: Session) {
      currentSession = session;
    },
    emit(event: string, session: Session) {
      currentSession = session;
      for (const listener of listeners) {
        listener(event, session);
      }
    },
    reset() {
      getUserMock.mockReset();
      hasSupabaseAuthConfigMock.mockReset();
      signInWithOAuthMock.mockReset();
      signOutMock.mockReset();
      onAuthStateChangeMock.mockClear();
      createClientMock.mockClear();
      unsubscribeMock.mockClear();
      listeners.clear();
      currentSession = null;

      hasSupabaseAuthConfigMock.mockReturnValue(true);
      signInWithOAuthMock.mockResolvedValue({ error: null });
      signOutMock.mockResolvedValue({ error: null });
      getUserMock.mockResolvedValue({ data: { user: null }, error: null });
    },
    signInUser(userId = "user-1") {
      currentSession = { user: { id: userId } };
      getUserMock.mockResolvedValue({
        data: { user: { id: userId } },
        error: null,
      });
    },
    signOutUser(message = "Auth session missing!") {
      currentSession = null;
      getUserMock.mockResolvedValue({
        data: { user: null },
        error: { message },
      });
    },
  };
}

const supabaseMock = vi.hoisted(createSupabaseMockHarness);

export function setupSupabaseMock() {
  return supabaseMock;
}

vi.mock("@/lib/supabase/client", () => ({
  createClient: supabaseMock.createClientMock,
}));

vi.mock("@/lib/supabase/config", () => ({
  hasSupabaseAuthConfig: supabaseMock.hasSupabaseAuthConfigMock,
}));
