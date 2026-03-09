import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BrowseAllPage from "./page";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("/browse-all page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("lists recipes alphabetically", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async () =>
      jsonResponse({
        recipes: [
          {
            id: "recipe-b",
            title: "Banana Bread",
            servings: "8",
            total_time: "1 hour",
            source_url: null,
            created_at: null,
            updated_at: null,
          },
          {
            id: "recipe-a",
            title: "Apple Pie",
            servings: "6",
            total_time: "50 minutes",
            source_url: null,
            created_at: null,
            updated_at: null,
          },
        ],
        count: 2,
        success: true,
      }),
    );

    render(<BrowseAllPage />);

    expect(await screen.findByText("All Recipes")).toBeInTheDocument();
    const cards = await screen.findAllByRole("button", { name: /^Open /i });
    expect(cards.map((card) => card.getAttribute("aria-label"))).toEqual([
      "Open Apple Pie",
      "Open Banana Bread",
    ]);
  });

  it("loads /all recipe payload when opening a card", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input) => {
      const path = String(input);
      if (path.startsWith("/api/recipes?")) {
        return jsonResponse({
          recipes: [
            {
              id: "recipe-1",
              title: "Creamy Pasta",
              servings: "2",
              total_time: "20 minutes",
              source_url: null,
              created_at: null,
              updated_at: null,
            },
          ],
          count: 1,
          success: true,
        });
      }

      if (path === "/api/recipes/recipe-1/all") {
        return jsonResponse({
          recipe: {
            id: "recipe-1",
            title: "Creamy Pasta",
            servings: "2",
            total_time: "20 minutes",
            source_url: null,
            created_at: null,
            updated_at: null,
            ingredients: ["Pasta", "Cream"],
            instructions: ["Cook pasta", "Add sauce"],
            embeddings: [],
          },
          success: true,
        });
      }

      return jsonResponse({ detail: "Unhandled request" }, 500);
    });

    const user = userEvent.setup();
    render(<BrowseAllPage />);

    const openCardButton = await screen.findByRole("button", {
      name: "Open Creamy Pasta",
    });
    await user.click(openCardButton);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/recipes/recipe-1/all", expect.any(Object));
    });

    const openFullPageLink = await screen.findByRole("link", {
      name: /Open Full Page/i,
    });
    expect(openFullPageLink).toHaveAttribute("href", "/recipes/recipe-1");
  });
});
