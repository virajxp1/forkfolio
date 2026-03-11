import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RecipeNotFoundPage from "./not-found";

describe("recipes/[recipeId] not-found page", () => {
  it("renders a custom not found message with recovery actions", () => {
    render(<RecipeNotFoundPage />);

    expect(screen.getByText("Recipe Not Found")).toBeInTheDocument();
    expect(screen.getByText("This recipe no longer exists.")).toBeInTheDocument();
    expect(
      screen.getByText("It may have been deleted, moved, or the link may be incorrect."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Browse Recipes" })).toHaveAttribute(
      "href",
      "/browse",
    );
    expect(
      screen
        .getAllByRole("link", { name: "Add Recipe" })
        .some((link) => link.getAttribute("href") === "/recipes/new"),
    ).toBe(true);
  });
});
