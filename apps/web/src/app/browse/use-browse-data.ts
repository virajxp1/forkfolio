"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type {
  RecipeListItem,
  RecipeRecord,
  SearchRecipeResult,
} from "@/lib/forkfolio-types";

import {
  MIN_QUERY_LENGTH,
  getErrorMessage,
  getRecipeClient,
  listRecipesClient,
  searchRecipesClient,
} from "./browse-api";
import { buildBrowseHref, normalizeParam } from "./browse-utils";

const SEARCH_LIMIT = 12;

type NavigationMode = "push" | "replace";

type DefaultListCache = {
  results: SearchRecipeResult[];
  nextCursor: string | null;
  hasMore: boolean;
};

function toSearchResults(recipes: RecipeListItem[]): SearchRecipeResult[] {
  return recipes.map((recipe) => ({
    id: recipe.id,
    name: recipe.title,
    distance: null,
  }));
}

function mergeSearchResults(
  currentResults: SearchRecipeResult[],
  incomingResults: SearchRecipeResult[],
): SearchRecipeResult[] {
  const seen = new Set<string>();
  const merged: SearchRecipeResult[] = [];
  for (const result of [...currentResults, ...incomingResults]) {
    const key = result.id ?? `${result.name ?? ""}-${result.distance ?? ""}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    merged.push(result);
  }
  return merged;
}

export function useBrowseData() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const queryFromUrl = normalizeParam(searchParams.get("q"));
  const recipeIdFromUrl = normalizeParam(searchParams.get("recipe"));

  const [queryInput, setQueryInput] = useState(queryFromUrl);
  const [results, setResults] = useState<SearchRecipeResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [defaultListNextCursor, setDefaultListNextCursor] = useState<string | null>(
    null,
  );
  const [defaultListHasMore, setDefaultListHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const [recipeById, setRecipeById] = useState<Record<string, RecipeRecord>>({});
  const [recipeLoadingById, setRecipeLoadingById] = useState<Record<string, boolean>>(
    {},
  );

  const [selectedRecipeLoading, setSelectedRecipeLoading] = useState(false);
  const [selectedRecipeError, setSelectedRecipeError] = useState<string | null>(null);

  const searchCacheRef = useRef<Record<string, SearchRecipeResult[]>>({});
  const defaultListCacheRef = useRef<DefaultListCache | null>(null);
  const recipeCacheRef = useRef<Record<string, RecipeRecord>>({});
  const inFlightRecipeRef = useRef<Record<string, Promise<RecipeRecord>>>({});
  const searchRequestIdRef = useRef(0);

  const setBrowseUrl = useCallback(
    (nextQuery: string, nextRecipeId?: string, navigation: NavigationMode = "push") => {
      const href = buildBrowseHref(nextQuery, nextRecipeId);
      if (navigation === "replace") {
        router.replace(href, { scroll: false });
        return;
      }
      router.push(href, { scroll: false });
    },
    [router],
  );

  const loadRecipeDetails = useCallback(async (recipeId: string): Promise<RecipeRecord> => {
    const cachedRecipe = recipeCacheRef.current[recipeId];
    if (cachedRecipe) {
      return cachedRecipe;
    }

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
        const recipeResponse = await getRecipeClient(recipeId);
        const recipe = recipeResponse.recipe;
        recipeCacheRef.current[recipeId] = recipe;

        setRecipeById((prev) => {
          if (prev[recipeId]) {
            return prev;
          }
          return {
            ...prev,
            [recipeId]: recipe,
          };
        });

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

  const prefetchResultDetails = useCallback(
    (searchResults: SearchRecipeResult[]) => {
      const ids = [
        ...new Set(
          searchResults
            .map((result) => result.id)
            .filter((recipeId): recipeId is string => Boolean(recipeId)),
        ),
      ];

      for (const recipeId of ids) {
        void loadRecipeDetails(recipeId).catch(() => null);
      }
    },
    [loadRecipeDetails],
  );

  const runSearch = useCallback(
    async (query: string) => {
      const requestId = searchRequestIdRef.current + 1;
      searchRequestIdRef.current = requestId;

      if (!query) {
        const cachedDefault = defaultListCacheRef.current;
        if (cachedDefault) {
          setResults(cachedDefault.results);
          setDefaultListNextCursor(cachedDefault.nextCursor);
          setDefaultListHasMore(cachedDefault.hasMore);
          setSearchError(null);
          setIsSearching(false);
          prefetchResultDetails(cachedDefault.results);
          return;
        }

        setIsSearching(true);
        setSearchError(null);
        setResults([]);
        setDefaultListNextCursor(null);
        setDefaultListHasMore(false);

        try {
          const listResponse = await listRecipesClient(SEARCH_LIMIT);
          if (searchRequestIdRef.current !== requestId) {
            return;
          }

          const nextResults = toSearchResults(listResponse.recipes ?? []);
          const nextCursor = listResponse.next_cursor ?? null;
          const hasMore = Boolean(listResponse.has_more && nextCursor);

          defaultListCacheRef.current = {
            results: nextResults,
            nextCursor,
            hasMore,
          };

          setResults(nextResults);
          setDefaultListNextCursor(nextCursor);
          setDefaultListHasMore(hasMore);
          setIsSearching(false);
          prefetchResultDetails(nextResults);
        } catch (error) {
          if (searchRequestIdRef.current !== requestId) {
            return;
          }
          setResults([]);
          setDefaultListNextCursor(null);
          setDefaultListHasMore(false);
          setIsSearching(false);
          setSearchError(getErrorMessage(error, "Failed to load recipes."));
        }
        return;
      }

      if (query.length < MIN_QUERY_LENGTH) {
        setResults([]);
        setDefaultListNextCursor(null);
        setDefaultListHasMore(false);
        setSearchError("Search query must be at least 2 characters.");
        setIsSearching(false);
        return;
      }

      const cachedResults = searchCacheRef.current[query];
      if (cachedResults) {
        setResults(cachedResults);
        setDefaultListNextCursor(null);
        setDefaultListHasMore(false);
        setSearchError(null);
        setIsSearching(false);
        prefetchResultDetails(cachedResults);
        return;
      }

      setIsSearching(true);
      setSearchError(null);
      setResults([]);
      setDefaultListNextCursor(null);
      setDefaultListHasMore(false);

      try {
        const searchResponse = await searchRecipesClient(query, SEARCH_LIMIT);
        if (searchRequestIdRef.current !== requestId) {
          return;
        }

        const nextResults = searchResponse.results ?? [];
        searchCacheRef.current[query] = nextResults;
        setResults(nextResults);
        setIsSearching(false);
        prefetchResultDetails(nextResults);
      } catch (error) {
        if (searchRequestIdRef.current !== requestId) {
          return;
        }
        setResults([]);
        setIsSearching(false);
        setSearchError(getErrorMessage(error, "Search request failed."));
      }
    },
    [prefetchResultDetails],
  );

  useEffect(() => {
    setQueryInput(queryFromUrl);
  }, [queryFromUrl]);

  useEffect(() => {
    void runSearch(queryFromUrl);
  }, [queryFromUrl, runSearch]);

  useEffect(() => {
    if (!recipeIdFromUrl) {
      setSelectedRecipeLoading(false);
      setSelectedRecipeError(null);
      return;
    }

    if (recipeCacheRef.current[recipeIdFromUrl]) {
      setSelectedRecipeLoading(false);
      setSelectedRecipeError(null);
      return;
    }

    let cancelled = false;
    setSelectedRecipeLoading(true);
    setSelectedRecipeError(null);

    void loadRecipeDetails(recipeIdFromUrl)
      .catch((error) => {
        if (!cancelled) {
          setSelectedRecipeError(getErrorMessage(error, "Failed to load recipe details."));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setSelectedRecipeLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [recipeIdFromUrl, loadRecipeDetails]);

  const selectedRecipe = useMemo(() => {
    if (!recipeIdFromUrl) {
      return null;
    }
    return recipeById[recipeIdFromUrl] ?? recipeCacheRef.current[recipeIdFromUrl] ?? null;
  }, [recipeById, recipeIdFromUrl]);

  const hasQuery = Boolean(queryFromUrl);
  const hasModal = Boolean(recipeIdFromUrl);
  const showInitialPrompt = false;
  const showLoadingGrid = isSearching && !results.length;
  const showNoResults = !searchError && !isSearching && !results.length;
  const showLoadMore = !hasQuery && !searchError && results.length > 0 && defaultListHasMore;

  function handleSearchSubmit() {
    const normalizedQuery = queryInput.trim();

    if (!normalizedQuery) {
      setBrowseUrl("", undefined, "replace");
      return;
    }

    setBrowseUrl(normalizedQuery, undefined, "push");
  }

  function handleQueryInputChange(nextQuery: string) {
    setQueryInput(nextQuery);

    if (nextQuery.trim() === "" && (queryFromUrl || recipeIdFromUrl)) {
      setBrowseUrl("", undefined, "replace");
    }
  }

  function openRecipeModal(recipeId: string) {
    setBrowseUrl(queryFromUrl, recipeId, "push");
  }

  function closeRecipeModal() {
    setBrowseUrl(queryFromUrl, undefined, "replace");
  }

  async function handleLoadMore() {
    if (hasQuery || isLoadingMore || !defaultListHasMore || !defaultListNextCursor) {
      return;
    }

    setIsLoadingMore(true);
    setSearchError(null);

    try {
      const listResponse = await listRecipesClient(SEARCH_LIMIT, defaultListNextCursor);
      const incomingResults = toSearchResults(listResponse.recipes ?? []);
      const nextCursor = listResponse.next_cursor ?? null;
      const hasMore = Boolean(listResponse.has_more && nextCursor);

      setDefaultListNextCursor(nextCursor);
      setDefaultListHasMore(hasMore);
      setResults((prev) => {
        const merged = mergeSearchResults(prev, incomingResults);
        defaultListCacheRef.current = {
          results: merged,
          nextCursor,
          hasMore,
        };
        return merged;
      });
      prefetchResultDetails(incomingResults);
    } catch (error) {
      setSearchError(getErrorMessage(error, "Failed to load more recipes."));
    } finally {
      setIsLoadingMore(false);
    }
  }

  return {
    queryFromUrl,
    queryInput,
    results,
    searchError,
    isSearching,
    recipeById,
    recipeLoadingById,
    recipeIdFromUrl,
    selectedRecipe,
    selectedRecipeLoading,
    selectedRecipeError,
    hasModal,
    showInitialPrompt,
    showLoadingGrid,
    showNoResults,
    showLoadMore,
    isLoadingMore,
    handleSearchSubmit,
    handleQueryInputChange,
    handleLoadMore,
    openRecipeModal,
    closeRecipeModal,
  };
}
