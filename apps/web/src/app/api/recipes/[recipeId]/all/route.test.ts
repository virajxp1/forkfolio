/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { getRecipeAllMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  getRecipeAllMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  getRecipeAll: getRecipeAllMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { GET } from "./route";

describe("GET /api/recipes/[recipeId]/all", () => {
  beforeEach(() => {
    getRecipeAllMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when recipe id is blank", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes//all");
    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "  " }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing recipe id." });
    expect(getRecipeAllMock).not.toHaveBeenCalled();
  });

  it("returns recipe-all payload and no-store cache header", async () => {
    getRecipeAllMock.mockResolvedValue({
      success: true,
      recipe: {
        id: "recipe-1",
        title: "Tomato Soup",
        servings: "2",
        total_time: "20 minutes",
        source_url: null,
        created_at: null,
        updated_at: null,
        ingredients: ["Tomatoes"],
        instructions: ["Cook"],
        embeddings: [],
      },
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/recipe-1/all");
    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "recipe-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(getRecipeAllMock).toHaveBeenCalledWith("recipe-1");
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe not found",
      message: "Recipe not found",
    };

    getRecipeAllMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes/missing/all");
    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "missing" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Recipe not found" });
  });
});
