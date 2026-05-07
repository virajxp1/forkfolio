/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  createRecipeBookMock,
  getRecipeBookByNameMock,
  isForkfolioApiErrorMock,
  listRecipeBooksMock,
} = vi.hoisted(() => ({
  createRecipeBookMock: vi.fn(),
  getRecipeBookByNameMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
  listRecipeBooksMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  createRecipeBook: createRecipeBookMock,
  getRecipeBookByName: getRecipeBookByNameMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
  listRecipeBooks: listRecipeBooksMock,
}));

import { GET, POST } from "./route";

describe("/api/recipe-books", () => {
  beforeEach(() => {
    createRecipeBookMock.mockReset();
    getRecipeBookByNameMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    listRecipeBooksMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("lists recipe books with default limit", async () => {
    listRecipeBooksMock.mockResolvedValue({
      recipe_books: [],
      success: true,
    });

    const request = new NextRequest("http://localhost:3000/api/recipe-books");
    const response = await GET(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(listRecipeBooksMock).toHaveBeenCalledWith(50);
    expect(getRecipeBookByNameMock).not.toHaveBeenCalled();
  });

  it("gets recipe book by name when name query param is present", async () => {
    getRecipeBookByNameMock.mockResolvedValue({
      recipe_book: { id: "book-1", name: "Dinner", recipe_ids: [] },
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/recipe-books?name=%20Dinner%20",
    );
    const response = await GET(request);

    expect(response.status).toBe(200);
    expect(getRecipeBookByNameMock).toHaveBeenCalledWith("Dinner");
    expect(listRecipeBooksMock).not.toHaveBeenCalled();
  });

  it("returns 400 when creating without name", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipe-books", {
      method: "POST",
      body: JSON.stringify({ description: "test" }),
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: "Missing name in request payload.",
    });
    expect(createRecipeBookMock).not.toHaveBeenCalled();
  });

  it("creates recipe book and trims payload fields", async () => {
    createRecipeBookMock.mockResolvedValue({
      recipe_book: { id: "book-1", name: "Dinner", recipe_count: 0 },
      created: true,
      success: true,
    });

    const request = new NextRequest("http://localhost:3000/api/recipe-books", {
      method: "POST",
      body: JSON.stringify({
        name: "  Dinner  ",
        description: "  Weeknight recipes  ",
      }),
      headers: { "Content-Type": "application/json" },
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(createRecipeBookMock).toHaveBeenCalledWith({
      name: "Dinner",
      description: "Weeknight recipes",
    });
  });

  it("maps forkfolio api errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe book not found",
      message: "Recipe book not found",
    };
    getRecipeBookByNameMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest(
      "http://localhost:3000/api/recipe-books?name=missing",
    );
    const response = await GET(request);

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({ detail: "Recipe book not found" });
  });
});
