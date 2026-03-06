import { render, screen, waitFor } from "@testing-library/react";
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

  it("renders results from search and prefetches recipe details", async () => {
    searchParams = new URLSearchParams("q=pasta");

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

    expect(await screen.findByText('Results for "pasta"')).toBeInTheDocument();
    expect(await screen.findByText("Creamy Pasta")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/search?query=pasta&limit=12",
      expect.objectContaining({ method: "GET" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/recipes/recipe-1",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("shows search error when API request fails", async () => {
    searchParams = new URLSearchParams("q=pasta");

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Backend unavailable" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<BrowsePage />);

    expect(await screen.findByText("Search Error")).toBeInTheDocument();
    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
  });
});
