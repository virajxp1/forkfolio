import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DeleteRecipeButton } from "./delete-recipe-button";

const { pushMock, refreshMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
  refreshMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
    refresh: refreshMock,
  }),
  usePathname: () => "/recipes/recipe-1",
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("DeleteRecipeButton", () => {
  beforeEach(() => {
    pushMock.mockReset();
    refreshMock.mockReset();
    vi.stubGlobal("fetch", vi.fn());
    vi.stubGlobal("confirm", vi.fn(() => true));
  });

  it("deletes recipe and redirects to browse", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(jsonResponse({ deleted: true, success: true }));

    const user = userEvent.setup();
    render(<DeleteRecipeButton recipeId="recipe-1" recipeTitle="Tomato Soup" />);

    await user.click(screen.getByRole("button", { name: /Delete Recipe/i }));

    expect(fetchMock).toHaveBeenCalledWith("/api/recipes/recipe-1", expect.any(Object));
    expect(pushMock).toHaveBeenCalledWith("/browse");
    expect(refreshMock).toHaveBeenCalledTimes(1);
  });

  it("does not call delete when confirmation is canceled", async () => {
    const fetchMock = vi.mocked(fetch);
    vi.stubGlobal("confirm", vi.fn(() => false));

    const user = userEvent.setup();
    render(<DeleteRecipeButton recipeId="recipe-1" recipeTitle="Tomato Soup" />);

    await user.click(screen.getByRole("button", { name: /Delete Recipe/i }));

    expect(fetchMock).not.toHaveBeenCalled();
    expect(pushMock).not.toHaveBeenCalled();
  });
});
