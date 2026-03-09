/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { previewRecipeFromUrlMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  previewRecipeFromUrlMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  previewRecipeFromUrl: previewRecipeFromUrlMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { POST } from "./route";

describe("POST /api/recipes/preview", () => {
  beforeEach(() => {
    previewRecipeFromUrlMock.mockReset();
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
    expect(previewRecipeFromUrlMock).not.toHaveBeenCalled();
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
    expect(previewRecipeFromUrlMock).not.toHaveBeenCalled();
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
    expect(previewRecipeFromUrlMock).not.toHaveBeenCalled();
  });

  it("trims url and forwards preview request", async () => {
    previewRecipeFromUrlMock.mockResolvedValue({
      success: true,
      created: false,
      url: "https://example.com/recipe",
      recipe_preview: {
        title: "Preview Title",
        ingredients: ["1 cup sugar"],
        instructions: ["Mix ingredients."],
        servings: "2",
        total_time: "10 minutes",
      },
      diagnostics: {
        raw_html_length: 1000,
        extracted_text_length: 800,
        cleaned_text_length: 700,
      },
      message: "Recipe preview generated successfully.",
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/preview", {
      method: "POST",
      body: JSON.stringify({ url: "  https://example.com/recipe  " }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(previewRecipeFromUrlMock).toHaveBeenCalledWith({
      url: "https://example.com/recipe",
    });
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 403,
      detail: "Blocked outbound URL fetch",
      message: "Blocked outbound URL fetch",
    };

    previewRecipeFromUrlMock.mockRejectedValue(apiError);
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

  it("maps backend 405 preview method errors to 503 with actionable detail", async () => {
    const apiError = {
      status: 405,
      detail: "Method Not Allowed",
      message: "Method Not Allowed",
    };

    previewRecipeFromUrlMock.mockRejectedValue(apiError);
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
    expect(await response.json()).toEqual({
      detail:
        "URL preview is not available on the configured backend deployment yet. Deploy the latest backend with POST /api/v1/recipes/preview-from-url.",
    });
  });
});
