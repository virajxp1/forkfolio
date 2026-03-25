/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { searchRecipesMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  searchRecipesMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  searchRecipes: searchRecipesMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { GET } from "./route";

describe("GET /api/search", () => {
  beforeEach(() => {
    searchRecipesMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when query is missing", async () => {
    const request = new NextRequest("http://localhost:3000/api/search");

    const response = await GET(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing query parameter." });
    expect(searchRecipesMock).not.toHaveBeenCalled();
  });

  it("calls searchRecipes and returns cacheable response", async () => {
    searchRecipesMock.mockResolvedValue({
      query: "pasta",
      count: 1,
      results: [{ id: "recipe-1", name: "Pasta", distance: 0.1 }],
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/search?query=pasta&limit=100",
    );

    const response = await GET(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe(
      "public, max-age=60, stale-while-revalidate=300",
    );
    expect(searchRecipesMock).toHaveBeenCalledWith("pasta", 50, false);
  });

  it("uses default limit when limit is invalid", async () => {
    searchRecipesMock.mockResolvedValue({
      query: "soup",
      count: 0,
      results: [],
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/search?query=soup&limit=invalid",
    );

    await GET(request);

    expect(searchRecipesMock).toHaveBeenCalledWith("soup", 12, false);
  });

  it("passes rerank flag through when explicitly enabled", async () => {
    searchRecipesMock.mockResolvedValue({
      query: "salad",
      count: 0,
      results: [],
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/search?query=salad&rerank=true",
    );

    await GET(request);

    expect(searchRecipesMock).toHaveBeenCalledWith("salad", 12, true);
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 429,
      detail: "Rate limit exceeded",
      message: "Rate limit exceeded",
    };

    searchRecipesMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/search?query=salad");
    const response = await GET(request);

    expect(response.status).toBe(429);
    expect(await response.json()).toEqual({ detail: "Rate limit exceeded" });
  });
});
