/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createRecipePreviewJobMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  createRecipePreviewJobMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  createRecipePreviewJob: createRecipePreviewJobMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { POST } from "./route";

describe("POST /api/recipes/preview", () => {
  beforeEach(() => {
    createRecipePreviewJobMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when url is missing", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/preview", {
      method: "POST",
      body: JSON.stringify({}),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: "Missing url in request payload.",
    });
    expect(createRecipePreviewJobMock).not.toHaveBeenCalled();
  });

  it("returns 422 when url is invalid", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/preview", {
      method: "POST",
      body: JSON.stringify({ url: "not-a-url" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({
      detail: "url must be a valid URL.",
    });
    expect(createRecipePreviewJobMock).not.toHaveBeenCalled();
  });

  it("returns 422 when url has unsupported scheme", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/preview", {
      method: "POST",
      body: JSON.stringify({ url: "ftp://example.com/recipe" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({
      detail: "url must use http or https.",
    });
    expect(createRecipePreviewJobMock).not.toHaveBeenCalled();
  });

  it("trims url and queues preview request", async () => {
    createRecipePreviewJobMock.mockResolvedValue({
      job_id: "job-123",
      status: "queued",
      url: "https://example.com/recipe",
      message: "Recipe preview import queued.",
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/preview", {
      method: "POST",
      body: JSON.stringify({ url: "  https://example.com/recipe  " }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(202);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(createRecipePreviewJobMock).toHaveBeenCalledWith({
      url: "https://example.com/recipe",
    });
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 403,
      detail: "Blocked outbound URL fetch",
      message: "Blocked outbound URL fetch",
    };

    createRecipePreviewJobMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes/preview", {
      method: "POST",
      body: JSON.stringify({ url: "https://example.com/recipe" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(403);
    expect(await response.json()).toEqual({ detail: "Blocked outbound URL fetch" });
  });

  it("maps backend errors for failed queue requests", async () => {
    const apiError = {
      status: 503,
      detail: "Preview worker unavailable",
      message: "Preview worker unavailable",
    };

    createRecipePreviewJobMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes/preview", {
      method: "POST",
      body: JSON.stringify({ url: "https://example.com/recipe" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({ detail: "Preview worker unavailable" });
  });
});
