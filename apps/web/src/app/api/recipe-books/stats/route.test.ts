/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { getRecipeBookStatsMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  getRecipeBookStatsMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  getRecipeBookStats: getRecipeBookStatsMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { GET } from "./route";

describe("GET /api/recipe-books/stats", () => {
  beforeEach(() => {
    getRecipeBookStatsMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns stats with no-store cache header", async () => {
    getRecipeBookStatsMock.mockResolvedValue({
      stats: {
        total_recipe_books: 1,
        total_recipe_book_links: 2,
        unique_recipes_in_books: 2,
        avg_recipes_per_book: 2,
      },
      success: true,
    });

    const response = await GET();

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(getRecipeBookStatsMock).toHaveBeenCalledTimes(1);
  });

  it("maps forkfolio api errors", async () => {
    const apiError = {
      status: 500,
      detail: "Stats unavailable",
      message: "Stats unavailable",
    };
    getRecipeBookStatsMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const response = await GET();

    expect(response.status).toBe(500);
    expect(await response.json()).toEqual({ detail: "Stats unavailable" });
  });
});
