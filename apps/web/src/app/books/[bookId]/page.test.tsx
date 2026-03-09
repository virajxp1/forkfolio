import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}), { virtual: true });

const { getRecipeBookMock, getRecipeMock, isForkfolioApiErrorMock, notFoundMock } =
  vi.hoisted(() => ({
    getRecipeBookMock: vi.fn(),
    getRecipeMock: vi.fn(),
    isForkfolioApiErrorMock: vi.fn(),
    notFoundMock: vi.fn(),
  }));

vi.mock("next/navigation", () => ({
  notFound: notFoundMock,
}));

vi.mock("@/lib/forkfolio-api", () => ({
  getRecipeBook: getRecipeBookMock,
  getRecipe: getRecipeMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import RecipeBookDetailPage from "./page";

const baseRecipeBook = {
  id: "book-1",
  name: "Dinner",
  normalized_name: "dinner",
  description: "Weeknight favorites",
  created_at: null,
  updated_at: null,
  recipe_count: 0,
};

const recipeRecord = {
  id: "recipe-1",
  title: "Tomato Curry",
  servings: "4",
  total_time: "30 minutes",
  source_url: null,
  created_at: null,
  updated_at: null,
  ingredients: ["Tomato", "Spices"],
  instructions: ["Cook"],
};

async function renderPage() {
  const page = await RecipeBookDetailPage({
    params: Promise.resolve({ bookId: "book-1" }),
  });
  render(page);
}

describe("/books/[bookId] page", () => {
  beforeEach(() => {
    getRecipeBookMock.mockReset();
    getRecipeMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    notFoundMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
  });

  it("shows empty-book state when recipe_ids is empty", async () => {
    getRecipeBookMock.mockResolvedValue({
      recipe_book: {
        ...baseRecipeBook,
        recipe_count: 0,
        recipe_ids: [],
      },
      success: true,
    });

    await renderPage();

    expect(await screen.findByText("No recipes in this book yet")).toBeInTheDocument();
    expect(screen.queryByText("Recipes are currently unavailable")).not.toBeInTheDocument();
    expect(getRecipeMock).not.toHaveBeenCalled();
  });

  it("shows partial-unavailable warning when some recipes fail", async () => {
    getRecipeBookMock.mockResolvedValue({
      recipe_book: {
        ...baseRecipeBook,
        recipe_count: 2,
        recipe_ids: ["recipe-1", "recipe-2"],
      },
      success: true,
    });

    getRecipeMock.mockImplementation((recipeId: string) => {
      if (recipeId === "recipe-1") {
        return Promise.resolve({ recipe: recipeRecord, success: true });
      }
      return Promise.reject(new Error("unavailable"));
    });

    await renderPage();

    expect(await screen.findByText("Some recipes could not be loaded")).toBeInTheDocument();
    expect(screen.queryByText("No recipes in this book yet")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Recipe/i })).toHaveAttribute(
      "href",
      "/recipes/recipe-1",
    );
  });

  it("shows unavailable state when all recipe fetches fail", async () => {
    getRecipeBookMock.mockResolvedValue({
      recipe_book: {
        ...baseRecipeBook,
        recipe_count: 2,
        recipe_ids: ["recipe-1", "recipe-2"],
      },
      success: true,
    });

    getRecipeMock.mockRejectedValue(new Error("unavailable"));

    await renderPage();

    expect(await screen.findByText("Recipes are currently unavailable")).toBeInTheDocument();
    expect(screen.queryByText("No recipes in this book yet")).not.toBeInTheDocument();
    expect(screen.queryByText("Some recipes could not be loaded")).not.toBeInTheDocument();
  });
});
