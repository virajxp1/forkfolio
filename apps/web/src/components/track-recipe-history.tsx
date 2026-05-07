"use client";

import { useEffect } from "react";

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
  }, [recipeId, recipeTitle]);

  return null;
}
