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
    fetchMock
      .mockResolvedValueOnce(
        listRecipesResponse({
          recipes: [{ id: "recipe-1", title: "Creamy Pasta" }],
          nextCursor: "cursor-1",
          hasMore: true,
        }),
      )
      .mockResolvedValueOnce(recipeResponse("recipe-1", "Creamy Pasta"))
      .mockReturnValueOnce(pendingLoadMore.promise)
      .mockResolvedValueOnce(
        jsonResponse({
          query: "pasta",
          count: 1,
          results: [{ id: "recipe-3", name: "Spicy Noodles", distance: 0.08 }],
          success: true,
        }),
      )
      .mockResolvedValueOnce(recipeResponse("recipe-3", "Spicy Noodles"));

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
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        query: "pasta",
        count: 0,
        results: [],
        success: true,
      }),
    );

    render(<BrowsePage />);

    expect(await screen.findByRole("searchbox")).toHaveValue("pasta");
    expect(await screen.findByText('Results for "pasta"')).toBeInTheDocument();
  });

  it("pushes normalized query to URL on submit", async () => {
    const user = userEvent.setup();

    render(<BrowsePage />);

    await user.type(screen.getByRole("searchbox"), "  creamy pasta  ");
    await user.click(screen.getByRole("button", { name: /^Search$/i }));

    expect(pushMock).toHaveBeenCalledWith("/browse?q=creamy+pasta", { scroll: false });
  });

  it("replaces URL when query input is cleared", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        query: "pasta",
        count: 0,
        results: [],
        success: true,
      }),
    );

    const user = userEvent.setup();
    render(<BrowsePage />);

    const input = await screen.findByRole("searchbox");
    await user.clear(input);

    expect(replaceMock).toHaveBeenCalledWith("/browse", { scroll: false });
  });

  it("pushes recipe modal route when opening a search card", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          query: "pasta",
          count: 1,
          results: [{ id: "recipe-1", name: "Creamy Pasta", distance: 0.05 }],
          success: true,
        }),
      )
      .mockResolvedValueOnce(recipeResponse());

    const user = userEvent.setup();
    render(<BrowsePage />);

    const openCardButton = await screen.findByRole("button", {
      name: "Open Creamy Pasta",
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    await user.click(openCardButton);

    expect(pushMock).toHaveBeenCalledWith("/browse?q=pasta&recipe=recipe-1", {
      scroll: false,
    });
  });

  it("replaces URL when closing an open modal", async () => {
    searchParams = new URLSearchParams("q=pasta&recipe=recipe-1");

    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({
          query: "pasta",
          count: 1,
          results: [{ id: "recipe-1", name: "Creamy Pasta", distance: 0.05 }],
          success: true,
        }),
      )
      .mockResolvedValueOnce(recipeResponse());

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
    fetchMock.mockResolvedValueOnce(
      jsonResponse({
        query: "kimchi",
        count: 0,
        results: [],
        success: true,
      }),
    );

    render(<BrowsePage />);

    expect(await screen.findByText("No recipes found")).toBeInTheDocument();
  });

  it("shows search error when API request fails", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          detail: "Backend unavailable",
        },
        500,
      ),
    );

    render(<BrowsePage />);

    expect(await screen.findByText("Search Error")).toBeInTheDocument();
    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
  });

  it("shows modal action to open full recipe page", async () => {
    searchParams = new URLSearchParams("q=pasta&recipe=recipe-1");

    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            query: "pasta",
            count: 1,
            results: [{ id: "recipe-1", name: "Creamy Pasta", distance: 0.05 }],
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
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

    render(<BrowsePage />);

    const openFullPageLink = await screen.findByRole("link", {
      name: /Open Full Page/i,
    });
    expect(openFullPageLink).toHaveAttribute("href", "/recipes/recipe-1");
  });
});
