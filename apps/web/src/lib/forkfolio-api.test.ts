/** @vitest-environment node */

import { afterEach, describe, expect, it, vi } from "vitest";

import { searchRecipes } from "./forkfolio-api";

describe("searchRecipes", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("uses the hybrid semantic endpoint for default search", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          query: "lasanga",
          count: 0,
          results: [],
          success: true,
        }),
        {
          status: 200,
          headers: { "Content-Type": "application/json" },
        },
      ),
    );

    await searchRecipes("lasanga", 12);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/recipes/search/semantic?query=lasanga&limit=12",
      expect.objectContaining({
        cache: "no-store",
      }),
    );
  });

});
