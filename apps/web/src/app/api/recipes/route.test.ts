/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { isForkfolioApiErrorMock, listRecipesMock } = vi.hoisted(() => ({
  isForkfolioApiErrorMock: vi.fn(),
  listRecipesMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  isForkfolioApiError: isForkfolioApiErrorMock,
  listRecipes: listRecipesMock,
}));

import { GET } from "./route";

describe("GET /api/recipes", () => {
  beforeEach(() => {
    isForkfolioApiErrorMock.mockReset();
    listRecipesMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("uses default limit when missing", async () => {
    listRecipesMock.mockResolvedValue({
      recipes: [],
      count: 0,
      success: true,
    });

    const request = new NextRequest("http://localhost:3000/api/recipes");
    const response = await GET(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(listRecipesMock).toHaveBeenCalledWith(200);
  });

  it("caps limit at max", async () => {
    listRecipesMock.mockResolvedValue({
      recipes: [],
      count: 0,
      success: true,
    });

    const request = new NextRequest("http://localhost:3000/api/recipes?limit=99999");
    await GET(request);

    expect(listRecipesMock).toHaveBeenCalledWith(1000);
  });

  it("maps forkfolio errors", async () => {
    const apiError = {
      status: 401,
      detail: "Unauthorized",
      message: "Unauthorized",
    };
    listRecipesMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes?limit=10");
    const response = await GET(request);

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Unauthorized" });
  });
});
