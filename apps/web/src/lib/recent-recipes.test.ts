import { beforeEach, describe, expect, it } from "vitest";

import {
  RECENT_RECIPES_STORAGE_KEY,
  readRecentRecipes,
  writeRecentRecipe,
} from "./recent-recipes";

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

describe("recent recipes storage", () => {
  let storage: Storage;

  beforeEach(() => {
    storage = createStorageMock();
  });

  it("writes a recent recipe and reads it back", () => {
    writeRecentRecipe(storage, {
      id: "recipe-1",
      title: "Tomato Soup",
    });

    const recentRecipes = readRecentRecipes(storage);
    expect(recentRecipes).toHaveLength(1);
    expect(recentRecipes[0]?.id).toBe("recipe-1");
    expect(recentRecipes[0]?.title).toBe("Tomato Soup");
  });

  it("moves existing recipe to the front when viewed again", () => {
    storage.setItem(
      RECENT_RECIPES_STORAGE_KEY,
      JSON.stringify([
        {
          id: "recipe-1",
          title: "Tomato Soup",
          viewed_at: "2025-01-01T00:00:00.000Z",
        },
        {
          id: "recipe-2",
          title: "Pasta",
          viewed_at: "2025-01-02T00:00:00.000Z",
        },
      ]),
    );

    writeRecentRecipe(storage, {
      id: "recipe-1",
      title: "Tomato Soup",
    });

    const recentRecipes = readRecentRecipes(storage);
    expect(recentRecipes[0]?.id).toBe("recipe-1");
    expect(recentRecipes[1]?.id).toBe("recipe-2");
  });
});
