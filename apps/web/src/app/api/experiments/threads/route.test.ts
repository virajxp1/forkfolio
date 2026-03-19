/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createExperimentThreadMock, isForkfolioApiErrorMock, listExperimentThreadsMock } = vi.hoisted(() => ({
  createExperimentThreadMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
  listExperimentThreadsMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  createExperimentThread: createExperimentThreadMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
  listExperimentThreads: listExperimentThreadsMock,
}));

import { GET, POST } from "./route";

describe("POST /api/experiments/threads", () => {
  beforeEach(() => {
    createExperimentThreadMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    listExperimentThreadsMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when JSON body is invalid", async () => {
    const request = new NextRequest("http://localhost:3000/api/experiments/threads", {
      method: "POST",
      body: "invalid-json",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Invalid JSON payload." });
    expect(createExperimentThreadMock).not.toHaveBeenCalled();
  });

  it("returns 422 when mode is invalid", async () => {
    const request = new NextRequest("http://localhost:3000/api/experiments/threads", {
      method: "POST",
      body: JSON.stringify({ mode: "wrong-mode" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({
      detail: "mode must be one of: invent_new, modify_existing.",
    });
    expect(createExperimentThreadMock).not.toHaveBeenCalled();
  });

  it("normalizes payload and forwards thread creation", async () => {
    createExperimentThreadMock.mockResolvedValue({
      success: true,
      thread: {
        id: "thread-1",
        mode: "invent_new",
        title: "Vegan weeknight curry",
        metadata: {},
        context_recipe_ids: ["recipe-1", "recipe-2"],
        messages: [],
        created_at: null,
        updated_at: null,
      },
    });

    const request = new NextRequest("http://localhost:3000/api/experiments/threads", {
      method: "POST",
      body: JSON.stringify({
        mode: "invent_new",
        title: "  Vegan weeknight curry  ",
        context_recipe_ids: ["recipe-1", "recipe-2", "recipe-1", " "],
        isTest: true,
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(createExperimentThreadMock).toHaveBeenCalledWith({
      mode: "invent_new",
      title: "Vegan weeknight curry",
      context_recipe_ids: ["recipe-1", "recipe-2"],
      is_test: true,
    });
  });

  it("returns 400 when is_test has invalid type", async () => {
    const request = new NextRequest("http://localhost:3000/api/experiments/threads", {
      method: "POST",
      body: JSON.stringify({
        mode: "invent_new",
        is_test: "true",
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: "is_test must be a boolean when provided.",
    });
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe missing",
      message: "Recipe missing",
    };
    createExperimentThreadMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/experiments/threads", {
      method: "POST",
      body: JSON.stringify({ mode: "invent_new" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Recipe missing" });
  });

  it("lists experiment threads", async () => {
    listExperimentThreadsMock.mockResolvedValue({
      success: true,
      count: 2,
      threads: [
        {
          id: "thread-1",
          mode: "invent_new",
          title: "Weeknight curry",
          metadata: {},
          created_at: null,
          updated_at: null,
          last_message_role: "assistant",
          last_message_content: "Try tofu and chickpeas.",
          last_message_created_at: null,
        },
        {
          id: "thread-2",
          mode: "invent_new",
          title: "Experiment E2E run",
          metadata: {},
          created_at: null,
          updated_at: null,
          last_message_role: "assistant",
          last_message_content: "Synthetic e2e response.",
          last_message_created_at: null,
        },
      ],
    });

    const request = new NextRequest("http://localhost:3000/api/experiments/threads?limit=10");
    const response = await GET(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(listExperimentThreadsMock).toHaveBeenCalledWith(10, false);
    expect(await response.json()).toMatchObject({ count: 1 });
  });

  it("includes test threads when include_test=true", async () => {
    listExperimentThreadsMock.mockResolvedValue({
      success: true,
      count: 2,
      threads: [
        {
          id: "thread-1",
          mode: "invent_new",
          title: "Weeknight curry",
          metadata: {},
          created_at: null,
          updated_at: null,
          last_message_role: "assistant",
          last_message_content: "Try tofu and chickpeas.",
          last_message_created_at: null,
        },
        {
          id: "thread-2",
          mode: "invent_new",
          title: "Experiment E2E run",
          metadata: { is_test: true },
          created_at: null,
          updated_at: null,
          last_message_role: "assistant",
          last_message_content: "Synthetic e2e response.",
          last_message_created_at: null,
        },
      ],
    });

    const request = new NextRequest(
      "http://localhost:3000/api/experiments/threads?limit=10&include_test=true",
    );
    const response = await GET(request);
    const body = await response.json();

    expect(response.status).toBe(200);
    expect(listExperimentThreadsMock).toHaveBeenCalledWith(10, true);
    expect(body.count).toBe(2);
    expect(body.threads).toHaveLength(2);
  });
});
