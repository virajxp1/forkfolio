/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

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
});
