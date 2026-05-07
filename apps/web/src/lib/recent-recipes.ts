export const RECENT_RECIPES_STORAGE_KEY = "forkfolio_recent_recipes";
const MAX_RECENT_RECIPES = 6;

export type RecentRecipeItem = {
  id: string;
  title: string;
  viewed_at: string;
};

function normalizeRecentRecipeItem(rawValue: unknown): RecentRecipeItem | null {
  if (!rawValue || typeof rawValue !== "object") {
    return null;
  }

  const record = rawValue as Record<string, unknown>;
  const id = typeof record.id === "string" ? record.id.trim() : "";
  const title = typeof record.title === "string" ? record.title.trim() : "";
  const viewedAt = typeof record.viewed_at === "string" ? record.viewed_at : "";

  if (!id || !title || !viewedAt) {
    return null;
  }

  return {
    id,
    title,
    viewed_at: viewedAt,
  };
}

export function readRecentRecipes(storage: Storage): RecentRecipeItem[] {
  const rawValue = storage.getItem(RECENT_RECIPES_STORAGE_KEY);
  if (!rawValue) {
    return [];
  }

  try {
    const parsedValue = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsedValue)) {
      return [];
    }

    return parsedValue
      .map(normalizeRecentRecipeItem)
      .filter((value): value is RecentRecipeItem => value !== null)
      .sort((left, right) => right.viewed_at.localeCompare(left.viewed_at))
      .slice(0, MAX_RECENT_RECIPES);
  } catch {
    return [];
  }
}

export function writeRecentRecipe(
  storage: Storage,
  recipe: {
    id: string;
    title: string;
  },
): void {
  const id = recipe.id.trim();
  const title = recipe.title.trim();
  if (!id || !title) {
    return;
  }

  const currentRecipes = readRecentRecipes(storage);
  const nextRecipes: RecentRecipeItem[] = [
    {
      id,
      title,
      viewed_at: new Date().toISOString(),
    },
    ...currentRecipes.filter((item) => item.id !== id),
  ].slice(0, MAX_RECENT_RECIPES);

  storage.setItem(RECENT_RECIPES_STORAGE_KEY, JSON.stringify(nextRecipes));
}
