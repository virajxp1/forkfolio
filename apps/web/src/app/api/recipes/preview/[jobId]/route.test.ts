/** @vitest-environment node */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { getRecipePreviewJobMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  getRecipePreviewJobMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  getRecipePreviewJob: getRecipePreviewJobMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { GET } from "./route";

describe("GET /api/recipes/preview/[jobId]", () => {
  beforeEach(() => {
    getRecipePreviewJobMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("returns 400 when job id is blank", async () => {
    const response = await GET(new Request("http://localhost:3000/api/recipes/preview/"), {
      params: Promise.resolve({ jobId: "   " }),
    });

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Missing recipe preview job id." });
    expect(getRecipePreviewJobMock).not.toHaveBeenCalled();
  });

  it("returns preview job payload with no-store cache header", async () => {
    getRecipePreviewJobMock.mockResolvedValue({
      job_id: "job-123",
      status: "completed",
      success: true,
      created: false,
      url: "https://example.com/recipe",
      recipe_preview: {
        title: "Preview Title",
        ingredients: ["1 cup sugar"],
        instructions: ["Mix ingredients."],
        servings: "2",
        total_time: "10 minutes",
      },
      diagnostics: {
        scrapegraphai_success: 1,
      },
      message: "Recipe preview generated successfully.",
    });

    const response = await GET(
      new Request("http://localhost:3000/api/recipes/preview/job-123"),
      {
        params: Promise.resolve({ jobId: "job-123" }),
      },
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(getRecipePreviewJobMock).toHaveBeenCalledWith("job-123");
  });

  it("maps backend errors", async () => {
    const apiError = {
      status: 404,
      detail: "Recipe preview job not found or expired.",
      message: "Recipe preview job not found or expired.",
    };

    getRecipePreviewJobMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const response = await GET(
      new Request("http://localhost:3000/api/recipes/preview/missing-job"),
      {
        params: Promise.resolve({ jobId: "missing-job" }),
      },
    );

    expect(response.status).toBe(404);
    expect(await response.json()).toEqual({
      detail: "Recipe preview job not found or expired.",
    });
  });
});
