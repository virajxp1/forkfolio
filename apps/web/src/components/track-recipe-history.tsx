"use client";

import { useEffect } from "react";

import { capturePostHogEvent } from "@/lib/posthog/client";
import { POSTHOG_EVENT } from "@/lib/posthog/events";
import { writeRecentRecipe } from "@/lib/recent-recipes";

export function TrackRecipeHistory({
  recipeId,
  recipeTitle,
}: {
  recipeId: string;
  recipeTitle: string;
}) {
  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    writeRecentRecipe(window.localStorage, {
      id: recipeId,
      title: recipeTitle,
    });
    capturePostHogEvent(POSTHOG_EVENT.RecipeViewed, {
      recipe_id: recipeId,
      source: "recipe_page",
    });
  }, [recipeId, recipeTitle]);

  return null;
}
