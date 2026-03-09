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

describe("/browse page", () => {
  beforeEach(() => {
    pushMock.mockReset();
    replaceMock.mockReset();
    searchParams = new URLSearchParams();
    vi.stubGlobal("fetch", vi.fn());
  });

  it("shows initial prompt when no query is provided", async () => {
    const fetchMock = vi.mocked(fetch);

    render(<BrowsePage />);

    expect(await screen.findByText("Start with a query")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
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
