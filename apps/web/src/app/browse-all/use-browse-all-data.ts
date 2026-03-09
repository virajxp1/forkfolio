"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { RecipeRecord, RecipeSummaryRecord, SearchRecipeResult } from "@/lib/forkfolio-types";

import { getErrorMessage, getRecipeAllClient, listRecipesClient } from "./browse-all-api";

function recipeTitleFromSummary(summary: RecipeSummaryRecord): string {
  return summary.title?.trim() || "Untitled recipe";
}

function summaryToSearchResult(summary: RecipeSummaryRecord): SearchRecipeResult {
  return {
    id: summary.id,
    name: recipeTitleFromSummary(summary),
    distance: null,
  };
}

function summaryToRecipeRecord(summary: RecipeSummaryRecord): RecipeRecord {
  return {
    id: summary.id,
    title: recipeTitleFromSummary(summary),
    servings: summary.servings,
    total_time: summary.total_time,
    source_url: summary.source_url,
    is_test_data: summary.is_test_data,
    created_at: summary.created_at,
    updated_at: summary.updated_at,
    ingredients: [],
    instructions: [],
  };
}

export function useBrowseAllData() {
  const [results, setResults] = useState<SearchRecipeResult[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const [recipeById, setRecipeById] = useState<Record<string, RecipeRecord>>({});
  const [recipeLoadingById, setRecipeLoadingById] = useState<Record<string, boolean>>(
    {},
  );
  const [recipeLoadedById, setRecipeLoadedById] = useState<Record<string, boolean>>({});

  const [selectedRecipeId, setSelectedRecipeId] = useState<string | null>(null);
  const [selectedRecipeLoading, setSelectedRecipeLoading] = useState(false);
  const [selectedRecipeError, setSelectedRecipeError] = useState<string | null>(null);

  const inFlightRecipeRef = useRef<Record<string, Promise<RecipeRecord>>>({});

  const loadRecipeDetails = useCallback(async (recipeId: string): Promise<RecipeRecord> => {
    const inFlight = inFlightRecipeRef.current[recipeId];
    if (inFlight) {
      return inFlight;
    }

    setRecipeLoadingById((prev) => {
      if (prev[recipeId]) {
        return prev;
      }
      return {
        ...prev,
        [recipeId]: true,
      };
    });

    const request = (async () => {
      try {
        const recipeResponse = await getRecipeAllClient(recipeId);
        const recipe = recipeResponse.recipe;

        setRecipeById((prev) => ({
          ...prev,
          [recipeId]: recipe,
        }));
        setRecipeLoadedById((prev) => ({
          ...prev,
          [recipeId]: true,
        }));

        return recipe;
      } finally {
        setRecipeLoadingById((prev) => {
          if (!prev[recipeId]) {
            return prev;
          }
          const next = { ...prev };
          delete next[recipeId];
          return next;
        });
      }
    })();

    inFlightRecipeRef.current[recipeId] = request;
    void request
      .finally(() => {
        if (inFlightRecipeRef.current[recipeId] === request) {
          delete inFlightRecipeRef.current[recipeId];
        }
      })
      .catch(() => undefined);

    return request;
  }, []);

  const loadAllRecipes = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    setResults([]);

    try {
      const listResponse = await listRecipesClient();
      const sortedRecipes = (listResponse.recipes ?? []).slice().sort((left, right) =>
        recipeTitleFromSummary(left).localeCompare(recipeTitleFromSummary(right), undefined, {
          sensitivity: "base",
        }),
      );
      setResults(sortedRecipes.map(summaryToSearchResult));
      setRecipeById(() => {
        const next: Record<string, RecipeRecord> = {};
        for (const summary of sortedRecipes) {
          next[summary.id] = summaryToRecipeRecord(summary);
        }
        return next;
      });
      setRecipeLoadedById({});
    } catch (error) {
      setLoadError(getErrorMessage(error, "Failed to load recipes."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAllRecipes();
  }, [loadAllRecipes]);

  const selectedRecipe = useMemo(() => {
    if (!selectedRecipeId || !recipeLoadedById[selectedRecipeId]) {
      return null;
    }
    return recipeById[selectedRecipeId] ?? null;
  }, [recipeById, recipeLoadedById, selectedRecipeId]);

  function openRecipeModal(recipeId: string) {
    setSelectedRecipeId(recipeId);
    setSelectedRecipeError(null);

    if (recipeLoadedById[recipeId]) {
      setSelectedRecipeLoading(false);
      return;
    }

    setSelectedRecipeLoading(true);
    void loadRecipeDetails(recipeId)
      .catch((error) => {
        setSelectedRecipeError(getErrorMessage(error, "Failed to load recipe details."));
      })
      .finally(() => {
        setSelectedRecipeLoading(false);
      });
  }

  function closeRecipeModal() {
    setSelectedRecipeId(null);
    setSelectedRecipeError(null);
    setSelectedRecipeLoading(false);
  }

  return {
    results,
    loadError,
    isLoading,
    recipeById,
    recipeLoadingById,
    selectedRecipeId,
    selectedRecipe,
    selectedRecipeLoading,
    selectedRecipeError,
    hasModal: Boolean(selectedRecipeId),
    showNoResults: !isLoading && !loadError && !results.length,
    openRecipeModal,
    closeRecipeModal,
    reloadAllRecipes: loadAllRecipes,
  };
}
