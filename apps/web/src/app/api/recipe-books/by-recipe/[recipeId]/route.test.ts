/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getRecipeBooksForRecipeMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  getRecipeBooksForRecipeMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  getRecipeBooksForRecipe: getRecipeBooksForRecipeMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { GET } from "./route";

describe("GET /api/recipe-books/by-recipe/[recipeId]", () => {
  beforeEach(() => {
    getRecipeBooksForRecipeMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when recipe id is blank", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipe-books/by-recipe/");
    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "  " }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing recipe id." });
    expect(getRecipeBooksForRecipeMock).not.toHaveBeenCalled();
  });

  it("returns recipe books for recipe with no-store cache header", async () => {
    getRecipeBooksForRecipeMock.mockResolvedValue({
      recipe_id: "recipe-1",
      recipe_books: [{ id: "book-1", name: "Dinner", recipe_count: 1 }],
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/recipe-books/by-recipe/recipe-1",
    );
    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "recipe-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(getRecipeBooksForRecipeMock).toHaveBeenCalledWith("recipe-1");
  });

  it("maps forkfolio api errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe not found",
      message: "Recipe not found",
    };
    getRecipeBooksForRecipeMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest(
      "http://localhost:3000/api/recipe-books/by-recipe/missing",
    );
    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "missing" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Recipe not found" });
  });
});
