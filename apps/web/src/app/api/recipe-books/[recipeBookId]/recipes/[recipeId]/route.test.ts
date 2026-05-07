/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { addRecipeToBookMock, isForkfolioApiErrorMock, removeRecipeFromBookMock } =
  vi.hoisted(() => ({
    addRecipeToBookMock: vi.fn(),
    isForkfolioApiErrorMock: vi.fn(),
    removeRecipeFromBookMock: vi.fn(),
  }));

vi.mock("@/lib/forkfolio-api", () => ({
  addRecipeToBook: addRecipeToBookMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
  removeRecipeFromBook: removeRecipeFromBookMock,
}));

import { DELETE, PUT } from "./route";

describe("/api/recipe-books/[recipeBookId]/recipes/[recipeId]", () => {
  beforeEach(() => {
    addRecipeToBookMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    removeRecipeFromBookMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 for blank recipe book id on PUT", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipe-books//recipes/r1", {
      method: "PUT",
    });
    const response = await PUT(request, {
      params: Promise.resolve({ recipeBookId: "  ", recipeId: "r1" }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing recipe book id." });
    expect(addRecipeToBookMock).not.toHaveBeenCalled();
  });

  it("adds recipe to recipe book on PUT", async () => {
    addRecipeToBookMock.mockResolvedValue({
      recipe_book_id: "book-1",
      recipe_id: "recipe-1",
      added: true,
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/recipe-books/book-1/recipes/recipe-1",
      { method: "PUT" },
    );
    const response = await PUT(request, {
      params: Promise.resolve({ recipeBookId: "book-1", recipeId: "recipe-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(addRecipeToBookMock).toHaveBeenCalledWith("book-1", "recipe-1");
  });

  it("removes recipe from recipe book on DELETE", async () => {
    removeRecipeFromBookMock.mockResolvedValue({
      recipe_book_id: "book-1",
      recipe_id: "recipe-1",
      removed: true,
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/recipe-books/book-1/recipes/recipe-1",
      { method: "DELETE" },
    );
    const response = await DELETE(request, {
      params: Promise.resolve({ recipeBookId: "book-1", recipeId: "recipe-1" }),
    });

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(removeRecipeFromBookMock).toHaveBeenCalledWith("book-1", "recipe-1");
  });

  it("maps forkfolio api errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe not found",
      message: "Recipe not found",
    };
    addRecipeToBookMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest(
      "http://localhost:3000/api/recipe-books/book-1/recipes/missing",
      { method: "PUT" },
    );
    const response = await PUT(request, {
      params: Promise.resolve({ recipeBookId: "book-1", recipeId: "missing" }),
    });

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Recipe not found" });
  });
});
