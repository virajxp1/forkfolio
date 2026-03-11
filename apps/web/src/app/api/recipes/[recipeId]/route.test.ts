/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { deleteRecipeApiMock, getRecipeApiMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  deleteRecipeApiMock: vi.fn(),
  getRecipeApiMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  deleteRecipe: deleteRecipeApiMock,
  getRecipe: getRecipeApiMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { DELETE, GET } from "./route";

describe("/api/recipes/[recipeId]", () => {
  beforeEach(() => {
    deleteRecipeApiMock.mockReset();
    getRecipeApiMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when recipe id is blank", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/");

    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "   " }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing recipe id." });
    expect(getRecipeApiMock).not.toHaveBeenCalled();
  });

  it("returns recipe payload and cacheable header", async () => {
    getRecipeApiMock.mockResolvedValue({
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
      },
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/recipe-1");
    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "recipe-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe(
      "public, max-age=300, stale-while-revalidate=900",
    );
    expect(getRecipeApiMock).toHaveBeenCalledWith("recipe-1");
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe not found",
      message: "Recipe not found",
    };

    getRecipeApiMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes/missing");
    const response = await GET(request, {
      params: Promise.resolve({ recipeId: "missing" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Recipe not found" });
  });

  it("returns 400 when deleting with blank recipe id", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/");

    const response = await DELETE(request, {
      params: Promise.resolve({ recipeId: "  " }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing recipe id." });
    expect(deleteRecipeApiMock).not.toHaveBeenCalled();
  });

  it("deletes recipe payload and no-store cache header", async () => {
    deleteRecipeApiMock.mockResolvedValue(true);

    const request = new NextRequest("http://localhost:3000/api/recipes/recipe-1");
    const response = await DELETE(request, {
      params: Promise.resolve({ recipeId: "recipe-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(await response.json()).toEqual({ deleted: true, success: true });
    expect(deleteRecipeApiMock).toHaveBeenCalledWith("recipe-1");
  });

  it("maps Forkfolio API errors for delete", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe not found",
      message: "Recipe not found",
    };

    deleteRecipeApiMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes/missing");
    const response = await DELETE(request, {
      params: Promise.resolve({ recipeId: "missing" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Recipe not found" });
  });
});
