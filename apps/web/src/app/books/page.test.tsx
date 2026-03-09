import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RecipeBooksPage from "./page";

describe("/books page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("loads and renders recipe books with stats", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            recipe_books: [
              {
                id: "book-1",
                name: "Weeknight Dinners",
                normalized_name: "weeknight dinners",
                description: "Quick meals",
                recipe_count: 3,
                created_at: null,
                updated_at: null,
              },
            ],
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            stats: {
              total_recipe_books: 1,
              total_recipe_book_links: 3,
              unique_recipes_in_books: 3,
              avg_recipes_per_book: 3,
            },
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    render(<RecipeBooksPage />);

    expect(await screen.findByText("Weeknight Dinners")).toBeInTheDocument();
    expect(await screen.findByText("Total Recipe Books")).toBeInTheDocument();
    expect((await screen.findAllByText("3")).length).toBeGreaterThanOrEqual(1);

    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/recipe-books?limit=200", {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/recipe-books/stats", {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
  });

  it("creates a recipe book and shows created state", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);

    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            recipe_books: [],
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            stats: {
              total_recipe_books: 0,
              total_recipe_book_links: 0,
              unique_recipes_in_books: 0,
              avg_recipes_per_book: 0,
            },
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            recipe_book: {
              id: "book-2",
              name: "Meal Prep",
              normalized_name: "meal prep",
              description: "Batch cooking",
              recipe_count: 0,
              created_at: null,
              updated_at: null,
            },
            created: true,
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            recipe_books: [
              {
                id: "book-2",
                name: "Meal Prep",
                normalized_name: "meal prep",
                description: "Batch cooking",
                recipe_count: 0,
                created_at: null,
                updated_at: null,
              },
            ],
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            stats: {
              total_recipe_books: 1,
              total_recipe_book_links: 0,
              unique_recipes_in_books: 0,
              avg_recipes_per_book: 0,
            },
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    render(<RecipeBooksPage />);

    await user.type(screen.getByLabelText("Name"), "Meal Prep");
    await user.type(screen.getByLabelText("Description (optional)"), "Batch cooking");
    await user.click(screen.getByRole("button", { name: /Create Recipe Book/i }));

    expect(await screen.findByText("Recipe book created")).toBeInTheDocument();
    expect((await screen.findAllByText("Meal Prep")).length).toBeGreaterThanOrEqual(1);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/recipe-books", {
        method: "POST",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: "Meal Prep",
          description: "Batch cooking",
        }),
      });
    });
  });
});
