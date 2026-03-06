import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NewRecipePage from "./page";

describe("/recipes/new page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  it("shows validation error when input is too short", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.mocked(fetch);

    render(<NewRecipePage />);

    await user.type(screen.getByLabelText("Raw recipe text"), "too short");
    await user.click(screen.getByRole("button", { name: "Process Recipe" }));

    expect(
      await screen.findByText("Recipe text must be at least 10 characters long."),
    ).toBeInTheDocument();
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
          message: "Recipe processed and stored successfully",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    render(<NewRecipePage />);

    await user.type(
      screen.getByLabelText("Raw recipe text"),
      "Chocolate Chip Cookies with flour, sugar, and butter.",
    );
    await user.click(screen.getByRole("button", { name: "Process Recipe" }));

    expect(await screen.findByText("Recipe saved")).toBeInTheDocument();
    expect(
      await screen.findByText("Recipe processed and stored successfully"),
    ).toBeInTheDocument();

    const detailsLink = screen.getByRole("link", { name: /View recipe details/i });
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
    await user.click(screen.getByRole("button", { name: "Process Recipe" }));

    expect(await screen.findByText("Unable to process recipe")).toBeInTheDocument();
    expect(await screen.findByText("Backend unavailable")).toBeInTheDocument();
  });
});
