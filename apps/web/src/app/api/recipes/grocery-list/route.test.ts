/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { createGroceryListMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  createGroceryListMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  createGroceryList: createGroceryListMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { POST } from "./route";

describe("POST /api/recipes/grocery-list", () => {
  beforeEach(() => {
    createGroceryListMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when recipe_ids is missing", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/grocery-list", {
      method: "POST",
      body: JSON.stringify({}),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: "recipe_ids must be a non-empty array of recipe IDs.",
    });
    expect(createGroceryListMock).not.toHaveBeenCalled();
  });

  it("returns 422 when recipe_ids resolves to empty IDs", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/grocery-list", {
      method: "POST",
      body: JSON.stringify({ recipe_ids: ["", "   "] }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({
      detail: "recipe_ids must include at least one recipe ID.",
    });
    expect(createGroceryListMock).not.toHaveBeenCalled();
  });

  it("trims, deduplicates, and forwards recipe IDs", async () => {
    createGroceryListMock.mockResolvedValue({
      recipe_ids: ["recipe-1", "recipe-2"],
      ingredients: ["1 onion", "2 tomatoes"],
      count: 2,
      success: true,
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/grocery-list", {
      method: "POST",
      body: JSON.stringify({
        recipe_ids: [" recipe-1 ", "recipe-2", "recipe-1"],
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(createGroceryListMock).toHaveBeenCalledWith({
      recipe_ids: ["recipe-1", "recipe-2"],
    });
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipes not found: recipe-9",
      message: "Recipes not found: recipe-9",
    };

    createGroceryListMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes/grocery-list", {
      method: "POST",
      body: JSON.stringify({ recipe_ids: ["recipe-9"] }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({
      detail: "Recipes not found: recipe-9",
    });
  });
});
