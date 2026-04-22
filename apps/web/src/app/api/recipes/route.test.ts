/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { listRecipesMock, isForkfolioApiErrorMock, getOptionalViewerUserIdMock } = vi.hoisted(
  () => ({
    listRecipesMock: vi.fn(),
    isForkfolioApiErrorMock: vi.fn(),
    getOptionalViewerUserIdMock: vi.fn(),
  }),
);

vi.mock("@/lib/forkfolio-api", () => ({
  listRecipes: listRecipesMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

vi.mock("@/lib/supabase/viewer", () => ({
  getOptionalViewerUserId: getOptionalViewerUserIdMock,
}));

import { GET } from "./route";

describe("GET /api/recipes", () => {
  beforeEach(() => {
    listRecipesMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    getOptionalViewerUserIdMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
    getOptionalViewerUserIdMock.mockResolvedValue(null);
  });

  it("uses default limit when limit is missing", async () => {
    listRecipesMock.mockResolvedValue({
      recipes: [],
      count: 0,
      limit: 12,
      cursor: null,
      next_cursor: null,
      has_more: false,
      success: true,
    });

    const request = new NextRequest("http://localhost:3000/api/recipes");
    const response = await GET(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe(
      "public, max-age=60, stale-while-revalidate=300",
    );
    expect(listRecipesMock).toHaveBeenCalledWith(12, undefined, null);
  });

  it("forwards cursor and caps limit at 200", async () => {
    listRecipesMock.mockResolvedValue({
      recipes: [],
      count: 0,
      limit: 200,
      cursor: "cursor-1",
      next_cursor: null,
      has_more: false,
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/recipes?limit=500&cursor=cursor-1",
    );
    await GET(request);

    expect(listRecipesMock).toHaveBeenCalledWith(200, "cursor-1", null);
  });

  it("uses default limit when limit is invalid", async () => {
    listRecipesMock.mockResolvedValue({
      recipes: [],
      count: 0,
      limit: 12,
      cursor: null,
      next_cursor: null,
      has_more: false,
      success: true,
    });

    const request = new NextRequest(
      "http://localhost:3000/api/recipes?limit=invalid",
    );
    await GET(request);

    expect(listRecipesMock).toHaveBeenCalledWith(12, undefined, null);
  });

  it("forwards viewer user id and disables shared caching", async () => {
    getOptionalViewerUserIdMock.mockResolvedValue("viewer-123");
    listRecipesMock.mockResolvedValue({
      recipes: [],
      count: 0,
      limit: 12,
      cursor: null,
      next_cursor: null,
      has_more: false,
      success: true,
    });

    const request = new NextRequest("http://localhost:3000/api/recipes");
    const response = await GET(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("private, no-store");
    expect(listRecipesMock).toHaveBeenCalledWith(12, undefined, "viewer-123");
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 401,
      detail: "Unauthorized",
      message: "Unauthorized",
    };

    listRecipesMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes");
    const response = await GET(request);

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Unauthorized" });
  });
});
