"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import type { GroceryBagItem, GroceryBagRecipe } from "@/lib/forkfolio-types";

const GROCERY_BAG_STORAGE_KEY = "forkfolio.grocery-bag.v1";

type GroceryBagContextValue = {
  items: GroceryBagItem[];
  itemCount: number;
  hasRecipe: (recipeId: string) => boolean;
  addRecipe: (recipe: GroceryBagRecipe) => void;
  removeRecipe: (recipeId: string) => void;
  clearBag: () => void;
};

const DEFAULT_CONTEXT_VALUE: GroceryBagContextValue = {
  items: [],
  itemCount: 0,
  hasRecipe: () => false,
  addRecipe: () => undefined,
  removeRecipe: () => undefined,
  clearBag: () => undefined,
};

const GroceryBagContext = createContext<GroceryBagContextValue>(DEFAULT_CONTEXT_VALUE);

function normalizeOptionalString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function sanitizeStoredItem(value: unknown): GroceryBagItem | null {
  if (!value || typeof value !== "object") {
    return null;
  }

  const candidate = value as Record<string, unknown>;
  const id = typeof candidate.id === "string" ? candidate.id.trim() : "";
  if (!id) {
    return null;
  }

  const title =
    typeof candidate.title === "string" && candidate.title.trim()
      ? candidate.title.trim()
      : "Untitled recipe";
  const addedAt =
    typeof candidate.added_at === "string" && candidate.added_at.trim()
      ? candidate.added_at
      : new Date().toISOString();

  return {
    id,
    title,
    servings: normalizeOptionalString(candidate.servings),
    total_time: normalizeOptionalString(candidate.total_time),
    added_at: addedAt,
  };
}

function dedupeByRecipeId(items: GroceryBagItem[]): GroceryBagItem[] {
  const byId = new Map<string, GroceryBagItem>();
  for (const item of items) {
    byId.set(item.id, item);
  }
  return Array.from(byId.values());
}

function readStoredBag(): GroceryBagItem[] {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const rawValue = window.localStorage.getItem(GROCERY_BAG_STORAGE_KEY);
    if (!rawValue) {
      return [];
    }
    const parsedValue = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsedValue)) {
      return [];
    }

    const sanitizedItems = parsedValue
      .map((entry) => sanitizeStoredItem(entry))
      .filter((entry): entry is GroceryBagItem => Boolean(entry));

    return dedupeByRecipeId(sanitizedItems);
  } catch {
    return [];
  }
}

export function GroceryBagProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<GroceryBagItem[]>([]);
  const hasLoadedPersistedState = useRef(false);

  useEffect(() => {
    // Read localStorage after mount so server-rendered HTML stays stable.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setItems(readStoredBag());
    hasLoadedPersistedState.current = true;
  }, []);

  useEffect(() => {
    if (!hasLoadedPersistedState.current || typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(GROCERY_BAG_STORAGE_KEY, JSON.stringify(items));
  }, [items]);

  const value = useMemo<GroceryBagContextValue>(() => {
    function hasRecipe(recipeId: string): boolean {
      const normalizedRecipeId = recipeId.trim();
      if (!normalizedRecipeId) {
        return false;
      }
      return items.some((item) => item.id === normalizedRecipeId);
    }

    function addRecipe(recipe: GroceryBagRecipe): void {
      const normalizedRecipeId = recipe.id.trim();
      if (!normalizedRecipeId) {
        return;
      }

      setItems((prev) => {
        if (prev.some((item) => item.id === normalizedRecipeId)) {
          return prev;
        }

        const normalizedTitle = recipe.title?.trim() || "Untitled recipe";
        return [
          ...prev,
          {
            id: normalizedRecipeId,
            title: normalizedTitle,
            servings: recipe.servings ?? null,
            total_time: recipe.total_time ?? null,
            added_at: new Date().toISOString(),
          },
        ];
      });
    }

    function removeRecipe(recipeId: string): void {
      const normalizedRecipeId = recipeId.trim();
      if (!normalizedRecipeId) {
        return;
      }
      setItems((prev) => prev.filter((item) => item.id !== normalizedRecipeId));
    }

    function clearBag(): void {
      setItems([]);
    }

    return {
      items,
      itemCount: items.length,
      hasRecipe,
      addRecipe,
      removeRecipe,
      clearBag,
    };
  }, [items]);

  return <GroceryBagContext.Provider value={value}>{children}</GroceryBagContext.Provider>;
}

export function useGroceryBag(): GroceryBagContextValue {
  return useContext(GroceryBagContext);
}
