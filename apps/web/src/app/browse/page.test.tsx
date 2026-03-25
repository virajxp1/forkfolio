import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BrowsePage from "./page";

const pushMock = vi.fn();
const replaceMock = vi.fn();
let searchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    replace: replaceMock,
  }),
  useSearchParams: () => searchParams,
  usePathname: () => "/browse",
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function recipeResponse(recipeId = "recipe-1", title = "Creamy Pasta"): Response {
  return jsonResponse({
    recipe: {
      id: recipeId,
      title,
      servings: "2",
      total_time: "20 minutes",
      source_url: null,
      created_at: null,
      updated_at: null,
      ingredients: ["Pasta", "Cream"],
      instructions: ["Cook pasta", "Add sauce"],
    },
    success: true,
  });
}

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

function listRecipesResponse({
  recipes = [],
  nextCursor = null,
  hasMore = false,
}: {
  recipes?: Array<{ id: string; title: string }>;
  nextCursor?: string | null;
  hasMore?: boolean;
} = {}): Response {
  return jsonResponse({
    recipes: recipes.map((recipe) => ({
      id: recipe.id,
      title: recipe.title,
      servings: null,
      total_time: null,
      source_url: null,
      created_at: null,
      updated_at: null,
    })),
    count: recipes.length,
    limit: 12,
    cursor: null,
    next_cursor: nextCursor,
    has_more: hasMore,
    success: true,
  });
}

function searchRecipesResponse({
  query,
  results = [],
}: {
  query: string;
  results?: Array<{ id: string | null; name: string | null; distance: number | null }>;
}): Response {
  return jsonResponse({
    query,
    count: results.length,
    results,
    success: true,
  });
}

function recipeResponseFromId(recipeId: string): Response {
  const titleById: Record<string, string> = {
    "recipe-1": "Creamy Pasta",
    "recipe-2": "Tomato Soup",
    "recipe-3": "Spicy Noodles",
  };
  return recipeResponse(recipeId, titleById[recipeId] ?? "Recipe");
}

describe("/browse page", () => {
  beforeEach(() => {
    pushMock.mockReset();
    replaceMock.mockReset();
    searchParams = new URLSearchParams();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(listRecipesResponse()));
  });

  it("loads recipe list when no query is provided", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        listRecipesResponse({
          recipes: [{ id: "recipe-1", title: "Creamy Pasta" }],
        }),
      )
      .mockResolvedValueOnce(recipeResponse());

    render(<BrowsePage />);

    expect(await screen.findByRole("button", { name: "Open Creamy Pasta" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/recipes?limit=12",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("loads more recipes when browsing without query", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        listRecipesResponse({
          recipes: [{ id: "recipe-1", title: "Creamy Pasta" }],
          nextCursor: "cursor-1",
          hasMore: true,
        }),
      )
      .mockResolvedValueOnce(recipeResponse("recipe-1", "Creamy Pasta"))
      .mockResolvedValueOnce(
        listRecipesResponse({
          recipes: [{ id: "recipe-2", title: "Tomato Soup" }],
          hasMore: false,
        }),
      )
      .mockResolvedValueOnce(recipeResponse("recipe-2", "Tomato Soup"));

    const user = userEvent.setup();
    render(<BrowsePage />);

    const loadMoreButton = await screen.findByRole("button", {
      name: "Load more recipes",
    });
    await user.click(loadMoreButton);

    expect(await screen.findByRole("button", { name: "Open Tomato Soup" })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/recipes?limit=12&cursor=cursor-1",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("ignores stale load-more responses after switching to query mode", async () => {
    const fetchMock = vi.mocked(fetch);
    const pendingLoadMore = createDeferred<Response>();
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url === "/api/recipes?limit=12") {
        return Promise.resolve(
          listRecipesResponse({
            recipes: [{ id: "recipe-1", title: "Creamy Pasta" }],
            nextCursor: "cursor-1",
            hasMore: true,
          }),
        );
      }
      if (url === "/api/recipes?limit=12&cursor=cursor-1") {
        return pendingLoadMore.promise;
      }
      if (url.startsWith("/api/search/names?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-3", name: "Spicy Noodles", distance: null }],
          }),
        );
      }
      if (url.startsWith("/api/search?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-3", name: "Spicy Noodles", distance: 0.08 }],
          }),
        );
      }
      if (url.startsWith("/api/recipes/")) {
        const recipeId = url.split("/").pop() ?? "recipe-1";
        return Promise.resolve(recipeResponseFromId(recipeId));
      }
      return Promise.resolve(listRecipesResponse());
    });

    const user = userEvent.setup();
    const { rerender } = render(<BrowsePage />);

    const loadMoreButton = await screen.findByRole("button", {
      name: "Load more recipes",
    });
    await user.click(loadMoreButton);

    searchParams = new URLSearchParams("q=pasta");
    rerender(<BrowsePage />);

    expect(await screen.findByRole("button", { name: "Open Spicy Noodles" })).toBeInTheDocument();

    pendingLoadMore.resolve(
      listRecipesResponse({
        recipes: [{ id: "recipe-2", title: "Tomato Soup" }],
        hasMore: false,
      }),
    );

    await waitFor(() => {
      expect(screen.queryByRole("button", { name: "Open Tomato Soup" })).not.toBeInTheDocument();
    });
  });

  it("shows short-query validation error without calling search API", async () => {
    searchParams = new URLSearchParams("q=a");
    const fetchMock = vi.mocked(fetch);

    render(<BrowsePage />);

    expect(
      await screen.findByText("Search query must be at least 2 characters."),
    ).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("syncs search input from URL query", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?") || url.startsWith("/api/search?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [],
          }),
        );
      }
      return Promise.resolve(listRecipesResponse());
    });

    render(<BrowsePage />);

    expect(await screen.findByRole("searchbox")).toHaveValue("pasta");
    expect(await screen.findByText('Results for "pasta"')).toBeInTheDocument();
  });

  it("loads text matches first, then lets users load related recipes", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    const deferredSemantic = createDeferred<Response>();
    const user = userEvent.setup();
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-1", name: "Creamy Pasta", distance: null }],
          }),
        );
      }
      if (url.startsWith("/api/search?")) {
        return deferredSemantic.promise;
      }
      if (url.startsWith("/api/recipes/")) {
        const recipeId = url.split("/").pop() ?? "recipe-1";
        return Promise.resolve(recipeResponseFromId(recipeId));
      }
      return Promise.resolve(listRecipesResponse());
    });

    render(<BrowsePage />);

    expect(await screen.findByRole("button", { name: "Open Creamy Pasta" })).toBeInTheDocument();
    expect(await screen.findByText("Related Recipes")).toBeInTheDocument();
    expect(await screen.findByText("Finding related recipes in the background...")).toBeInTheDocument();

    deferredSemantic.resolve(
      searchRecipesResponse({
        query: "pasta",
        results: [
          { id: "recipe-1", name: "Creamy Pasta", distance: 0.05 },
          { id: "recipe-3", name: "Spicy Noodles", distance: 0.08 },
        ],
      }),
    );

    const loadRelatedButton = await screen.findByRole("button", {
      name: "Load related recipes (1)",
    });
    await user.click(loadRelatedButton);

    expect(await screen.findByRole("button", { name: "Open Spicy Noodles" })).toBeInTheDocument();
  });

  it("shows refining hint while semantic rerank runs in the background", async () => {
    searchParams = new URLSearchParams("q=noodles");

    const fetchMock = vi.mocked(fetch);
    const deferredRerank = createDeferred<Response>();
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?")) {
        return Promise.resolve(jsonResponse({ detail: "name search down" }, 500));
      }
      if (url.startsWith("/api/search?")) {
        if (url.includes("rerank=true")) {
          return deferredRerank.promise;
        }
        return Promise.resolve(
          searchRecipesResponse({
            query: "noodles",
            results: [
              { id: "recipe-1", name: "Creamy Pasta", distance: 0.12 },
              { id: "recipe-3", name: "Spicy Noodles", distance: 0.18 },
            ],
          }),
        );
      }
      if (url.startsWith("/api/recipes/")) {
        const recipeId = url.split("/").pop() ?? "recipe-1";
        return Promise.resolve(recipeResponseFromId(recipeId));
      }
      return Promise.resolve(listRecipesResponse());
    });

    render(<BrowsePage />);

    expect(await screen.findByRole("button", { name: "Open Creamy Pasta" })).toBeInTheDocument();
    expect(await screen.findByText("Refining results...")).toBeInTheDocument();

    deferredRerank.resolve(
      searchRecipesResponse({
        query: "noodles",
        results: [
          { id: "recipe-3", name: "Spicy Noodles", distance: 0.08 },
          { id: "recipe-1", name: "Creamy Pasta", distance: 0.10 },
        ],
      }),
    );

    await waitFor(() => {
      expect(screen.queryByText("Refining results...")).not.toBeInTheDocument();
    });
  });

  it("keeps fast semantic results when background rerank returns no results", async () => {
    searchParams = new URLSearchParams("q=noodles");

    const fetchMock = vi.mocked(fetch);
    const deferredRerank = createDeferred<Response>();
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?")) {
        return Promise.resolve(jsonResponse({ detail: "name search down" }, 500));
      }
      if (url.startsWith("/api/search?")) {
        if (url.includes("rerank=true")) {
          return deferredRerank.promise;
        }
        return Promise.resolve(
          searchRecipesResponse({
            query: "noodles",
            results: [
              { id: "recipe-1", name: "Creamy Pasta", distance: 0.12 },
              { id: "recipe-3", name: "Spicy Noodles", distance: 0.18 },
            ],
          }),
        );
      }
      if (url.startsWith("/api/recipes/")) {
        const recipeId = url.split("/").pop() ?? "recipe-1";
        return Promise.resolve(recipeResponseFromId(recipeId));
      }
      return Promise.resolve(listRecipesResponse());
    });

    render(<BrowsePage />);

    expect(await screen.findByRole("button", { name: "Open Creamy Pasta" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Open Spicy Noodles" })).toBeInTheDocument();
    expect(await screen.findByText("Refining results...")).toBeInTheDocument();

    deferredRerank.resolve(
      searchRecipesResponse({
        query: "noodles",
        results: [],
      }),
    );

    await waitFor(() => {
      expect(screen.queryByText("Refining results...")).not.toBeInTheDocument();
    });

    expect(screen.getByRole("button", { name: "Open Creamy Pasta" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Spicy Noodles" })).toBeInTheDocument();
  });

  it("pushes normalized query to URL on submit", async () => {
    const user = userEvent.setup();

    render(<BrowsePage />);

    await user.type(screen.getByRole("searchbox"), "  creamy pasta  ");
    const searchButton = await screen.findByRole("button", { name: /^Search$/i });
    await user.click(searchButton);

    expect(pushMock).toHaveBeenCalledWith("/browse?q=creamy+pasta", { scroll: false });
  });

  it("replaces URL when query input is cleared", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?") || url.startsWith("/api/search?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [],
          }),
        );
      }
      return Promise.resolve(listRecipesResponse());
    });

    const user = userEvent.setup();
    render(<BrowsePage />);

    const input = await screen.findByRole("searchbox");
    await user.clear(input);

    expect(replaceMock).toHaveBeenCalledWith("/browse", { scroll: false });
  });

  it("pushes recipe modal route when opening a search card", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-1", name: "Creamy Pasta", distance: null }],
          }),
        );
      }
      if (url.startsWith("/api/search?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-1", name: "Creamy Pasta", distance: 0.05 }],
          }),
        );
      }
      if (url.startsWith("/api/recipes/")) {
        return Promise.resolve(recipeResponse());
      }
      return Promise.resolve(listRecipesResponse());
    });

    const user = userEvent.setup();
    render(<BrowsePage />);

    const openCardButton = await screen.findByRole("button", {
      name: "Open Creamy Pasta",
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    await user.click(openCardButton);

    expect(pushMock).toHaveBeenCalledWith("/browse?q=pasta&recipe=recipe-1", {
      scroll: false,
    });
  });

  it("replaces URL when closing an open modal", async () => {
    searchParams = new URLSearchParams("q=pasta&recipe=recipe-1");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-1", name: "Creamy Pasta", distance: null }],
          }),
        );
      }
      if (url.startsWith("/api/search?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-1", name: "Creamy Pasta", distance: 0.05 }],
          }),
        );
      }
      if (url.startsWith("/api/recipes/")) {
        return Promise.resolve(recipeResponse());
      }
      return Promise.resolve(listRecipesResponse());
    });

    const user = userEvent.setup();
    render(<BrowsePage />);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    const closeButtons = screen.getAllByRole("button", {
      name: "Close recipe details",
    });
    await user.click(closeButtons[0]);

    expect(replaceMock).toHaveBeenCalledWith("/browse?q=pasta", { scroll: false });
  });

  it("shows no-results state when search returns empty", async () => {
    searchParams = new URLSearchParams("q=kimchi");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?") || url.startsWith("/api/search?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "kimchi",
            results: [],
          }),
        );
      }
      return Promise.resolve(listRecipesResponse());
    });

    render(<BrowsePage />);

    expect(await screen.findByText("No recipes found")).toBeInTheDocument();
  });

  it("shows search error when API request fails", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [],
          }),
        );
      }
      if (url.startsWith("/api/search?")) {
        return Promise.resolve(
          jsonResponse(
            {
              detail: "Backend unavailable",
            },
            500,
          ),
        );
      }
      return Promise.resolve(listRecipesResponse());
    });

    render(<BrowsePage />);

    expect(await screen.findByText("Search Error")).toBeInTheDocument();
    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
  });

  it("shows modal action to open full recipe page", async () => {
    searchParams = new URLSearchParams("q=pasta&recipe=recipe-1");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation((input) => {
      const url = String(input);
      if (url.startsWith("/api/search/names?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-1", name: "Creamy Pasta", distance: null }],
          }),
        );
      }
      if (url.startsWith("/api/search?")) {
        return Promise.resolve(
          searchRecipesResponse({
            query: "pasta",
            results: [{ id: "recipe-1", name: "Creamy Pasta", distance: 0.05 }],
          }),
        );
      }
      if (url.startsWith("/api/recipes/")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
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
              },
              success: true,
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      return Promise.resolve(listRecipesResponse());
    });

    render(<BrowsePage />);

    const openFullPageLink = await screen.findByRole("link", {
      name: /Open Full Page/i,
    });
    expect(openFullPageLink).toHaveAttribute("href", "/recipes/recipe-1");
  });
});
