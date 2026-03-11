import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GroceryBagProvider } from "./grocery-bag-provider";
import { ForkfolioHeader } from "./forkfolio-header";

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

function renderHeader() {
  return render(
    <GroceryBagProvider>
      <ForkfolioHeader />
    </GroceryBagProvider>,
  );
}

describe("ForkfolioHeader", () => {
  let localStorageMock: LocalStorageMock;

  beforeEach(() => {
    localStorageMock = createLocalStorageMock();
    vi.stubGlobal("localStorage", localStorageMock);
    Object.defineProperty(window, "localStorage", {
      value: localStorageMock,
      configurable: true,
    });
  });

  it("shows bag count and hover preview for saved recipes", async () => {
    localStorageMock.setItem(
      "forkfolio.grocery-bag.v1",
      JSON.stringify([
        {
          id: "recipe-1",
          title: "Creamy Pasta",
          servings: "2 servings",
          total_time: "20 minutes",
          added_at: "2026-03-10T01:00:00.000Z",
        },
        {
          id: "recipe-2",
          title: "Tomato Soup",
          servings: "4 servings",
          total_time: "35 minutes",
          added_at: "2026-03-10T01:05:00.000Z",
        },
      ]),
    );

    const user = userEvent.setup();
    renderHeader();

    const bagLink = await screen.findByRole("link", { name: /Bag/i });
    await waitFor(() => {
      expect(bagLink).toHaveTextContent("2");
    });

    await user.hover(bagLink);

    expect(await screen.findByText("Bag Preview")).toBeInTheDocument();
    expect(await screen.findByText("Creamy Pasta")).toBeInTheDocument();
    expect(await screen.findByText("Tomato Soup")).toBeInTheDocument();
  });
});
