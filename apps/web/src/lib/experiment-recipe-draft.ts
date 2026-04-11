export const EXPERIMENT_RECIPE_DRAFT_STORAGE_KEY = "forkfolio:experiment-recipe-draft";

export function saveExperimentRecipeDraft(content: string): boolean {
  const normalizedContent = content.trim();
  if (!normalizedContent || typeof window === "undefined") {
    return false;
  }

  try {
    window.sessionStorage.setItem(
      EXPERIMENT_RECIPE_DRAFT_STORAGE_KEY,
      normalizedContent,
    );
    return true;
  } catch {
    return false;
  }
}

export function consumeExperimentRecipeDraft(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const storedContent = window.sessionStorage.getItem(
      EXPERIMENT_RECIPE_DRAFT_STORAGE_KEY,
    );
    window.sessionStorage.removeItem(EXPERIMENT_RECIPE_DRAFT_STORAGE_KEY);
    const normalizedContent = storedContent?.trim() ?? "";
    return normalizedContent || null;
  } catch {
    return null;
  }
}
