import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RecipeBookMembership } from "./recipe-book-membership";

describe("RecipeBookMembership", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("loads recipe books and marks current memberships", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            recipe_books: [
              {
                id: "book-1",
                name: "Dinner",
                normalized_name: "dinner",
                description: null,
                recipe_count: 2,
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
            recipe_id: "recipe-1",
            recipe_books: [
              {
                id: "book-1",
                name: "Dinner",
                normalized_name: "dinner",
                description: null,
                recipe_count: 2,
                created_at: null,
                updated_at: null,
              },
            ],
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    render(<RecipeBookMembership recipeId="recipe-1" />);

    expect(await screen.findByText("Dinner")).toBeInTheDocument();
    expect(await screen.findByText("In Book")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Remove/i })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("adds recipe to book", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);
    fetchMock
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            recipe_books: [
              {
                id: "book-2",
                name: "Lunch",
                normalized_name: "lunch",
                description: null,
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
            recipe_id: "recipe-1",
            recipe_books: [],
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            recipe_book_id: "book-2",
            recipe_id: "recipe-1",
            added: true,
            success: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      );

    render(<RecipeBookMembership recipeId="recipe-1" />);

    await user.click(await screen.findByRole("button", { name: /^Add$/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/recipe-books/book-2/recipes/recipe-1",
        {
          method: "PUT",
          cache: "no-store",
          headers: { Accept: "application/json" },
        },
      );
    });

    expect(await screen.findByRole("button", { name: /Remove/i })).toBeInTheDocument();
  });
});
