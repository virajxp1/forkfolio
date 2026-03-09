import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import HomePage from "./page";

const { pushMock } = vi.hoisted(() => ({
  pushMock: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function createStorageMock(): Storage {
  const store = new Map<string, string>();

  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key) ?? null : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, value);
    },
  };
}

describe("HomePage", () => {
  beforeEach(() => {
    pushMock.mockReset();
    Object.defineProperty(window, "localStorage", {
      value: createStorageMock(),
      configurable: true,
    });
    vi.stubGlobal("fetch", vi.fn());
  });

  it("renders discoverability cards and quick search chips", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async () =>
      jsonResponse({
        recipe_books: [],
        success: true,
      }),
    );

    render(<HomePage />);

    expect(await screen.findByText("What You Can Do")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Add New Recipe" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Search" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Books" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "curry" })).toHaveAttribute(
      "href",
      "/browse?q=curry",
    );
  });

  it("shows recent recipes when local history exists", async () => {
    window.localStorage.setItem(
      "forkfolio_recent_recipes",
      JSON.stringify([
        {
          id: "recipe-1",
          title: "Tomato Soup",
          viewed_at: "2026-01-01T12:00:00.000Z",
        },
      ]),
    );

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async () =>
      jsonResponse({
        recipe_books: [],
        success: true,
      }),
    );

    render(<HomePage />);

    expect(await screen.findByText("Continue where you left off")).toBeInTheDocument();
    expect(screen.getByText("Tomato Soup")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Recipe" })).toHaveAttribute(
      "href",
      "/recipes/recipe-1",
    );
  });
});
