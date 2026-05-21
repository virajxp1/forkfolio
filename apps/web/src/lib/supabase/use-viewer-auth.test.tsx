import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { setupSupabaseMock } from "@/test/supabase-mock";

import { useViewerAuth } from "./use-viewer-auth";

const supabaseMock = setupSupabaseMock();

describe("useViewerAuth", () => {
  beforeEach(() => {
    supabaseMock.reset();
  });

  it("resolves a signed-in viewer from INITIAL_SESSION without calling getUser on mount", async () => {
    supabaseMock.signInUser("viewer-1");

    const { result } = renderHook(() => useViewerAuth());

    await waitFor(() => {
      expect(result.current.auth).toEqual({ status: "ready", viewerUserId: "viewer-1" });
    });
    expect(supabaseMock.getUserMock).not.toHaveBeenCalled();
    expect(result.current.isViewerActive("viewer-1")).toBe(true);
  });

  it("blocks access when the initial session is signed out", async () => {
    supabaseMock.signOutUser();

    const { result } = renderHook(() => useViewerAuth());

    await waitFor(() => {
      expect(result.current.auth).toEqual({
        status: "blocked",
        reason: "auth_required",
        error: null,
      });
    });
    expect(result.current.isViewerActive("viewer-1")).toBe(false);
  });

  it("retries auth resolution with getUser and restores ready state", async () => {
    supabaseMock.signOutUser();

    const { result } = renderHook(() => useViewerAuth());

    await waitFor(() => {
      expect(result.current.auth).toEqual({
        status: "blocked",
        reason: "auth_required",
        error: null,
      });
    });

    supabaseMock.signInUser("viewer-2");

    await act(async () => {
      await result.current.retry();
    });

    expect(result.current.auth).toEqual({ status: "ready", viewerUserId: "viewer-2" });
    expect(supabaseMock.getUserMock).toHaveBeenCalledTimes(1);
  });

  it("updates when auth state changes after mount", async () => {
    supabaseMock.signInUser("viewer-1");

    const { result } = renderHook(() => useViewerAuth());

    await waitFor(() => {
      expect(result.current.auth).toEqual({ status: "ready", viewerUserId: "viewer-1" });
    });

    act(() => {
      supabaseMock.emit("SIGNED_OUT", null);
    });

    await waitFor(() => {
      expect(result.current.auth).toEqual({
        status: "blocked",
        reason: "auth_required",
        error: null,
      });
    });

    act(() => {
      supabaseMock.emit("SIGNED_IN", { user: { id: "viewer-2" } });
    });

    await waitFor(() => {
      expect(result.current.auth).toEqual({ status: "ready", viewerUserId: "viewer-2" });
    });
  });
});
