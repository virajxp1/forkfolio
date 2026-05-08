/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getRequiredViewerUserIdMock } = vi.hoisted(() => ({
  getRequiredViewerUserIdMock: vi.fn(),
}));

vi.mock("@/lib/supabase/viewer", () => ({
  getRequiredViewerUserId: getRequiredViewerUserIdMock,
}));

import { POST } from "./route";

function createSseResponse(events: string, status = 200): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(events));
      controller.close();
    },
  });
  return new Response(stream, {
    status,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("POST /api/experiments/threads/[threadId]/messages/stream", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    getRequiredViewerUserIdMock.mockReset();
    getRequiredViewerUserIdMock.mockResolvedValue({ viewerUserId: "user-123" });
  });

  it("returns 400 when content is missing", async () => {
    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages/stream",
      {
        method: "POST",
        body: JSON.stringify({}),
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    const response = await POST(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: "Missing content in request payload.",
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("returns 400 when attach recipe IDs are invalid", async () => {
    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages/stream",
      {
        method: "POST",
        body: JSON.stringify({
          content: "Make this vegan",
          attach_recipe_ids: "not-an-array",
        }),
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    const response = await POST(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: "attach_recipe_ids must be an array of strings.",
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("proxies SSE stream from backend", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      createSseResponse("event: status\ndata: {\"step\":\"drafting\"}\n\n"),
    );

    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages/stream",
      {
        method: "POST",
        body: JSON.stringify({ content: "Make this vegan" }),
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    const response = await POST(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("text/event-stream");
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/experiments/threads/thread-1/messages/stream"),
      expect.objectContaining({ method: "POST" }),
    );
    const upstreamHeaders = fetchMock.mock.calls[0]?.[1]?.headers;
    expect(upstreamHeaders).toBeInstanceOf(Headers);
    expect((upstreamHeaders as Headers).get("X-Viewer-User-Id")).toBe("user-123");
    expect(await response.text()).toContain("event: status");
  });

  it("maps upstream errors", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Thread not found" }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages/stream",
      {
        method: "POST",
        body: JSON.stringify({ content: "Make this vegan" }),
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    const response = await POST(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Thread not found" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("returns 401 when the user is not signed in", async () => {
    getRequiredViewerUserIdMock.mockResolvedValue({
      viewerUserId: null,
      detail: "Sign in to use experiment threads.",
      status: 401,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages/stream",
      {
        method: "POST",
        body: JSON.stringify({ content: "Make this vegan" }),
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    const response = await POST(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({
      detail: "Sign in to use experiment threads.",
    });
    expect(fetch).not.toHaveBeenCalled();
  });
});
