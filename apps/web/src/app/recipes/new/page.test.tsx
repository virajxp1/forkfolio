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

    await user.click(screen.getByRole("tab", { name: /Paste Text/i }));
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

    await user.click(screen.getByRole("tab", { name: /Paste Text/i }));
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

  it("fetches URL preview and saves it directly", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          success: true,
          created: false,
          url: "https://example.com/pasta",
          recipe_preview: {
            title: "Lemon Garlic Pasta",
            ingredients: ["200g spaghetti", "2 cloves garlic"],
            instructions: ["Boil pasta.", "Saute garlic.", "Toss and serve."],
            servings: "2",
            total_time: "20 minutes",
          },
          diagnostics: {
            raw_html_length: 1200,
            extracted_text_length: 900,
            cleaned_text_length: 700,
          },
          message: "Recipe preview generated successfully.",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          success: true,
          recipe_id: "recipe-preview-123",
          created: true,
          message: "Recipe processed and stored successfully",
          recipe: {
            id: "recipe-preview-123",
            title: "Lemon Garlic Pasta",
            servings: "2",
            total_time: "20 minutes",
            source_url: null,
            created_at: null,
            updated_at: null,
            ingredients: ["200g spaghetti", "2 cloves garlic"],
            instructions: ["Boil pasta.", "Saute garlic.", "Toss and serve."],
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<NewRecipePage />);

    await user.type(screen.getByLabelText("Recipe URL"), "https://example.com/pasta");
    await user.click(screen.getByRole("button", { name: /Fetch URL Preview/i }));

    expect(await screen.findByText("Lemon Garlic Pasta")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^Save Recipe$/i }));

    expect(await screen.findByText("Created")).toBeInTheDocument();
    expect(await screen.findByText("Recipe processed and stored successfully")).toBeInTheDocument();
    const detailsLink = screen.getByRole("link", { name: /Open Recipe/i });
    expect(detailsLink).toHaveAttribute("href", "/recipes/recipe-preview-123");
    expect(screen.getByRole("button", { name: /Save Another Recipe/i })).toBeInTheDocument();
    expect(screen.queryByLabelText("Recipe URL")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Raw recipe text")).not.toBeInTheDocument();
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

    await user.click(screen.getByRole("tab", { name: /Paste Text/i }));
    await user.type(
      screen.getByLabelText("Raw recipe text"),
      "Long enough recipe text for API processing",
    );
    await user.click(screen.getByRole("button", { name: /Process & Save Recipe/i }));

    expect(await screen.findByText("Unable to process recipe")).toBeInTheDocument();
    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
  });
});
