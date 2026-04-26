/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getExperimentThreadMock, isForkfolioApiErrorMock, getRequiredViewerUserIdMock } =
  vi.hoisted(() => ({
    getExperimentThreadMock: vi.fn(),
    isForkfolioApiErrorMock: vi.fn(),
    getRequiredViewerUserIdMock: vi.fn(),
  }));

vi.mock("@/lib/forkfolio-api", () => ({
  getExperimentThread: getExperimentThreadMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

vi.mock("@/lib/supabase/viewer", () => ({
  getRequiredViewerUserId: getRequiredViewerUserIdMock,
}));

import { GET } from "./route";

describe("GET /api/experiments/threads/[threadId]", () => {
  beforeEach(() => {
    getExperimentThreadMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    getRequiredViewerUserIdMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
    getRequiredViewerUserIdMock.mockResolvedValue({ viewerUserId: "user-123" });
  });

  it("returns 400 when thread id is blank", async () => {
    const request = new NextRequest("http://localhost:3000/api/experiments/threads/");

    const response = await GET(request, {
      params: Promise.resolve({ threadId: "   " }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing thread id." });
    expect(getExperimentThreadMock).not.toHaveBeenCalled();
  });

  it("returns thread payload and no-store cache header", async () => {
    getExperimentThreadMock.mockResolvedValue({
      success: true,
      thread: {
        id: "thread-1",
        mode: "invent_new",
        title: null,
        metadata: {},
        context_recipe_ids: [],
        messages: [],
        created_at: null,
        updated_at: null,
      },
    });

    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1?message_limit=200",
    );
    const response = await GET(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(getExperimentThreadMock).toHaveBeenCalledWith("thread-1", 200, "user-123");
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 404,
      detail: "Experiment thread not found",
      message: "Experiment thread not found",
    };
    getExperimentThreadMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/experiments/threads/thread-1");
    const response = await GET(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Experiment thread not found" });
  });

  it("returns 401 when the user is not signed in", async () => {
    getRequiredViewerUserIdMock.mockResolvedValue({
      viewerUserId: null,
      detail: "Sign in to use experiment threads.",
      status: 401,
    });

    const request = new NextRequest("http://localhost:3000/api/experiments/threads/thread-1");
    const response = await GET(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({
      detail: "Sign in to use experiment threads.",
    });
    expect(getExperimentThreadMock).not.toHaveBeenCalled();
  });
});
