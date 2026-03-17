/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { searchRecipesByNameMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  searchRecipesByNameMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  searchRecipesByName: searchRecipesByNameMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { GET } from "./route";

describe("GET /api/search/names", () => {
  beforeEach(() => {
    searchRecipesByNameMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when query is missing", async () => {
    const request = new NextRequest("http://localhost:3000/api/search/names");

    const response = await GET(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing query parameter." });
    expect(searchRecipesByNameMock).not.toHaveBeenCalled();
  });

  it("returns 422 when query is shorter than 3 chars", async () => {
    const request = new NextRequest(
      "http://localhost:3000/api/search/names?query=ab",
    );

    const response = await GET(request);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({
      detail: "Query must contain at least 3 characters.",
    });
    expect(searchRecipesByNameMock).not.toHaveBeenCalled();
  });

  it("calls searchRecipesByName and returns cacheable response", async () => {
    searchRecipesByNameMock.mockResolvedValue({
      query: "chi",
      count: 1,
      results: [{ id: "recipe-1", name: "Chicken Tikka Masala", distance: null }],
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/search/names?query=chi&limit=99",
    );

    const response = await GET(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe(
      "public, max-age=15, stale-while-revalidate=60",
    );
    expect(searchRecipesByNameMock).toHaveBeenCalledWith("chi", 10);
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 429,
      detail: "Rate limit exceeded",
      message: "Rate limit exceeded",
    };

    searchRecipesByNameMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest(
      "http://localhost:3000/api/search/names?query=chicken",
    );
    const response = await GET(request);

    expect(response.status).toBe(429);
    expect(await response.json()).toEqual({ detail: "Rate limit exceeded" });
  });
});
