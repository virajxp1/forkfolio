import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NewRecipePage from "./page";

describe("/recipes/new page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("disables submit while input is too short", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);

    render(<NewRecipePage />);

    await user.type(screen.getByLabelText("Raw recipe text"), "too short");

    expect(screen.getByRole("button", { name: /Process & Save Recipe/i })).toBeDisabled();
    expect(screen.getByText(/\(1 more needed\)/i)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows success state when recipe processing succeeds", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          recipe_id: "recipe-123",
          created: true,
          message: "Recipe processed and stored successfully",
          recipe: {
            id: "recipe-123",
            title: "Chocolate Chip Cookies",
            servings: null,
            total_time: null,
            source_url: null,
            created_at: null,
            updated_at: null,
            ingredients: [],
            instructions: [],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<NewRecipePage />);

    await user.type(
      screen.getByLabelText("Raw recipe text"),
      "Chocolate Chip Cookies with flour, sugar, and butter.",
    );
    await user.click(screen.getByRole("button", { name: /Process & Save Recipe/i }));

    expect(await screen.findByText("Created")).toBeInTheDocument();
    expect(
      await screen.findByText("Recipe processed and stored successfully"),
    ).toBeInTheDocument();
    expect(await screen.findByText("Chocolate Chip Cookies")).toBeInTheDocument();

    const detailsLink = screen.getByRole("link", { name: /Open Recipe/i });
    expect(detailsLink).toHaveAttribute("href", "/recipes/recipe-123");
  });

  it("shows error state when API returns failure", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "Backend unavailable" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      }),
    );

    render(<NewRecipePage />);

    await user.type(
      screen.getByLabelText("Raw recipe text"),
      "Long enough recipe text for API processing",
    );
    await user.click(screen.getByRole("button", { name: /Process & Save Recipe/i }));

    expect(await screen.findByText("Unable to process recipe")).toBeInTheDocument();
    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
  });
});
