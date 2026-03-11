import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GroceryBagProvider } from "@/components/grocery-bag-provider";

import GroceryBagPage from "./page";

function renderWithProvider() {
  return render(
    <GroceryBagProvider>
      <GroceryBagPage />
    </GroceryBagProvider>,
  );
}

type LocalStorageMock = {
  getItem: (key: string) => string | null;
  setItem: (key: string, value: string) => void;
  removeItem: (key: string) => void;
  clear: () => void;
};

function createLocalStorageMock(): LocalStorageMock {
  let storage: Record<string, string> = {};
  return {
    getItem: (key: string) => storage[key] ?? null,
    setItem: (key: string, value: string) => {
      storage[key] = value;
    },
    removeItem: (key: string) => {
      delete storage[key];
    },
    clear: () => {
      storage = {};
    },
  };
}

describe("/bag page", () => {
  let localStorageMock: LocalStorageMock;

  beforeEach(() => {
    localStorageMock = createLocalStorageMock();
    vi.stubGlobal("localStorage", localStorageMock);
    Object.defineProperty(window, "localStorage", {
      value: localStorageMock,
      configurable: true,
    });
    vi.stubGlobal("fetch", vi.fn());
  });

  it("shows empty state when bag has no recipes", async () => {
    renderWithProvider();

    expect(await screen.findByText("Your bag is empty")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Generate Grocery List/i }),
    ).toBeDisabled();
  });

  it("submits recipe IDs at checkout and renders generated list", async () => {
    localStorageMock.setItem(
      "forkfolio.grocery-bag.v1",
      JSON.stringify([
        {
          id: "recipe-1",
          title: "Creamy Pasta",
          servings: "2",
          total_time: "20 minutes",
          added_at: "2026-03-10T01:00:00.000Z",
        },
        {
          id: "recipe-2",
          title: "Tomato Soup",
          servings: "4",
          total_time: "35 minutes",
          added_at: "2026-03-10T01:05:00.000Z",
        },
      ]),
    );

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          recipe_ids: ["recipe-1", "recipe-2"],
          ingredients: ["1 lb pasta", "3 tomatoes"],
          count: 2,
          success: true,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const user = userEvent.setup();
    renderWithProvider();

    expect(await screen.findByText("Creamy Pasta")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Generate Grocery List/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith("/api/recipes/grocery-list", {
        method: "POST",
        cache: "no-store",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          recipe_ids: ["recipe-1", "recipe-2"],
        }),
      });
    });

    expect(await screen.findByText("Your Grocery List")).toBeInTheDocument();
    expect(await screen.findByText("1 lb pasta")).toBeInTheDocument();
  });
});
