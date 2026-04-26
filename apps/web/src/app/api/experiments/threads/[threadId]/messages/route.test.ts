/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createExperimentMessageMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  createExperimentMessageMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  createExperimentMessage: createExperimentMessageMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { POST } from "./route";

describe("POST /api/experiments/threads/[threadId]/messages", () => {
  beforeEach(() => {
    createExperimentMessageMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when content is missing", async () => {
    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages",
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
    expect(createExperimentMessageMock).not.toHaveBeenCalled();
  });

  it("returns 400 when context recipe IDs are invalid", async () => {
    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages",
      {
        method: "POST",
        body: JSON.stringify({
          content: "Make this vegan",
          context_recipe_ids: "not-an-array",
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
      detail: "context_recipe_ids must be an array of strings.",
    });
    expect(createExperimentMessageMock).not.toHaveBeenCalled();
  });

  it("returns 400 when attach recipe names are invalid", async () => {
    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages",
      {
        method: "POST",
        body: JSON.stringify({
          content: "Make this vegan",
          attach_recipe_names: "not-an-array",
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
      detail: "attach_recipe_names must be an array of strings.",
    });
    expect(createExperimentMessageMock).not.toHaveBeenCalled();
  });

  it("returns 400 when attach recipe IDs are invalid", async () => {
    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages",
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
    expect(createExperimentMessageMock).not.toHaveBeenCalled();
  });

  it("normalizes payload and forwards message creation", async () => {
    createExperimentMessageMock.mockResolvedValue({
      success: true,
      thread_id: "thread-1",
      thread: {
        id: "thread-1",
        title: null,
        metadata: {},
        context_recipe_ids: ["recipe-1"],
        messages: [],
        created_at: null,
        updated_at: null,
      },
      user_message: {
        id: "msg-user",
        thread_id: "thread-1",
        sequence_no: 1,
        role: "user",
        content: "Make this vegan",
        tool_name: null,
        tool_call: null,
        created_at: null,
      },
      assistant_message: {
        id: "msg-assistant",
        thread_id: "thread-1",
        sequence_no: 2,
        role: "assistant",
        content: "Use tofu and coconut yogurt.",
        tool_name: null,
        tool_call: null,
        created_at: null,
      },
    });

    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages",
      {
        method: "POST",
        body: JSON.stringify({
          content: "  Make this vegan  ",
          context_recipe_ids: ["recipe-1", "recipe-1", " "],
          attach_recipe_ids: ["recipe-1", "recipe-1", " "],
        }),
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    const response = await POST(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(createExperimentMessageMock).toHaveBeenCalledWith("thread-1", {
      content: "Make this vegan",
      context_recipe_ids: ["recipe-1"],
      attach_recipe_ids: ["recipe-1"],
    });
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 404,
      detail: "Experiment thread not found",
      message: "Experiment thread not found",
    };
    createExperimentMessageMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads/thread-1/messages",
      {
        method: "POST",
        body: JSON.stringify({ content: "hello" }),
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    const response = await POST(request, {
      params: Promise.resolve({ threadId: "thread-1" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Experiment thread not found" });
  });
});
