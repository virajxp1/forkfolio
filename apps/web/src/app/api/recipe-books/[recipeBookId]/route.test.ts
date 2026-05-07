/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getRecipeBookMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  getRecipeBookMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  getRecipeBook: getRecipeBookMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { GET } from "./route";

describe("GET /api/recipe-books/[recipeBookId]", () => {
  beforeEach(() => {
    getRecipeBookMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when recipe book id is blank", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipe-books/");
    const response = await GET(request, {
      params: Promise.resolve({ recipeBookId: "   " }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing recipe book id." });
    expect(getRecipeBookMock).not.toHaveBeenCalled();
  });

  it("returns recipe book payload and no-store cache header", async () => {
    getRecipeBookMock.mockResolvedValue({
      recipe_book: {
        id: "book-1",
        name: "Dinner",
        recipe_ids: ["recipe-1"],
      },
      success: true,
    });

    const request = new NextRequest("http://localhost:3000/api/recipe-books/book-1");
    const response = await GET(request, {
      params: Promise.resolve({ recipeBookId: "book-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(getRecipeBookMock).toHaveBeenCalledWith("book-1");
  });

  it("maps forkfolio api errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe book not found",
      message: "Recipe book not found",
    };

    getRecipeBookMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipe-books/missing");
    const response = await GET(request, {
      params: Promise.resolve({ recipeBookId: "missing" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Recipe book not found" });
  });
});
