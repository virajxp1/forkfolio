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
  MIN_TEXT_MATCH_QUERY_LENGTH,
  getErrorMessage,
  getRecipeClient,
  listRecipesClient,
  searchRecipesClient,
  searchRecipesByNameClient,
} from "./browse-api";
import { buildBrowseHref, normalizeParam } from "./browse-utils";

const SEARCH_LIMIT = 12;

type NavigationMode = "push" | "replace";
type SearchMatchSource = "browse" | "text" | "semantic";

export type BrowseSearchResult = SearchRecipeResult & {
  matchSource: SearchMatchSource;
  semanticDistance: number | null;
};

type DefaultListCache = {
  results: BrowseSearchResult[];
  nextCursor: string | null;
  hasMore: boolean;
};

type SearchCacheEntry = {
  baseResults: BrowseSearchResult[];
  relatedResults: BrowseSearchResult[];
};

function toBrowseResults(recipes: RecipeListItem[]): BrowseSearchResult[] {
  return recipes.map((recipe) => ({
    id: recipe.id,
    name: recipe.title,
    distance: null,
    matchSource: "browse",
    semanticDistance: null,
  }));
}

function getSearchResultKey(result: Pick<SearchRecipeResult, "id" | "name" | "distance">) {
  return result.id ?? `${result.name ?? ""}-${result.distance ?? ""}`;
}

function dedupeSearchResults(results: SearchRecipeResult[]): SearchRecipeResult[] {
  const seen = new Set<string>();
  const deduped: SearchRecipeResult[] = [];
  for (const result of results) {
    const key = getSearchResultKey(result);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(result);
  }
  return deduped;
}

function toMatchSourceResults(
  results: SearchRecipeResult[],
  source: "text" | "semantic",
): BrowseSearchResult[] {
  return dedupeSearchResults(results).map((result) => ({
    ...result,
    matchSource: source,
    semanticDistance: source === "semantic" ? result.distance ?? null : null,
  }));
}

function mergeBrowseResults(
  currentResults: BrowseSearchResult[],
  incomingResults: BrowseSearchResult[],
): BrowseSearchResult[] {
  const seen = new Set<string>();
  const merged: BrowseSearchResult[] = [];
  for (const result of [...currentResults, ...incomingResults]) {
    const key = getSearchResultKey(result);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    merged.push(result);
  }
  return merged;
}

function getRelatedSemanticResults(
  baseResults: BrowseSearchResult[],
  semanticResults: BrowseSearchResult[],
): BrowseSearchResult[] {
  const baseKeys = new Set(baseResults.map((result) => getSearchResultKey(result)));
  return semanticResults.filter((result) => !baseKeys.has(getSearchResultKey(result)));
}

export function useBrowseData() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const queryFromUrl = normalizeParam(searchParams.get("q"));
  const recipeIdFromUrl = normalizeParam(searchParams.get("recipe"));

  const [queryInput, setQueryInput] = useState(queryFromUrl);
  const [results, setResults] = useState<BrowseSearchResult[]>([]);
  const [relatedResults, setRelatedResults] = useState<BrowseSearchResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingRelated, setIsLoadingRelated] = useState(false);
  const [hasLoadedRelated, setHasLoadedRelated] = useState(false);
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

  const searchCacheRef = useRef<Record<string, SearchCacheEntry>>({});
  const defaultListCacheRef = useRef<DefaultListCache | null>(null);
  const recipeCacheRef = useRef<Record<string, RecipeRecord>>({});
  const inFlightRecipeRef = useRef<Record<string, Promise<RecipeRecord>>>({});
  const searchRequestIdRef = useRef(0);
  const isBrowseModeRef = useRef(!queryFromUrl);

  isBrowseModeRef.current = !queryFromUrl;

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
    (searchResults: BrowseSearchResult[]) => {
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
          setRelatedResults([]);
          setHasLoadedRelated(false);
          setDefaultListNextCursor(cachedDefault.nextCursor);
          setDefaultListHasMore(cachedDefault.hasMore);
          setSearchError(null);
          setIsSearching(false);
          setIsLoadingRelated(false);
          prefetchResultDetails(cachedDefault.results);
          return;
        }

        setIsSearching(true);
        setIsLoadingRelated(false);
        setSearchError(null);
        setResults([]);
        setRelatedResults([]);
        setHasLoadedRelated(false);
        setDefaultListNextCursor(null);
        setDefaultListHasMore(false);

        try {
          const listResponse = await listRecipesClient(SEARCH_LIMIT);
          if (searchRequestIdRef.current !== requestId) {
            return;
          }

          const nextResults = toBrowseResults(listResponse.recipes ?? []);
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
        setRelatedResults([]);
        setHasLoadedRelated(false);
        setDefaultListNextCursor(null);
        setDefaultListHasMore(false);
        setIsLoadingRelated(false);
        setSearchError("Search query must be at least 2 characters.");
        setIsSearching(false);
        return;
      }

      const cachedSearch = searchCacheRef.current[query];
      if (cachedSearch) {
        setResults(cachedSearch.baseResults);
        setRelatedResults(cachedSearch.relatedResults);
        setHasLoadedRelated(false);
        setDefaultListNextCursor(null);
        setDefaultListHasMore(false);
        setSearchError(null);
        setIsSearching(false);
        setIsLoadingRelated(false);
        prefetchResultDetails(cachedSearch.baseResults);
        if (cachedSearch.relatedResults.length > 0) {
          prefetchResultDetails(cachedSearch.relatedResults);
        }
        return;
      }

      setIsSearching(true);
      setIsLoadingRelated(false);
      setSearchError(null);
      setResults([]);
      setRelatedResults([]);
      setHasLoadedRelated(false);
      setDefaultListNextCursor(null);
      setDefaultListHasMore(false);

      let baseResults: BrowseSearchResult[] = [];
      let useSemanticAsPrimary = query.length < MIN_TEXT_MATCH_QUERY_LENGTH;

      if (!useSemanticAsPrimary) {
        try {
          const textResponse = await searchRecipesByNameClient(query, SEARCH_LIMIT);
          if (searchRequestIdRef.current !== requestId) {
            return;
          }

          baseResults = toMatchSourceResults(textResponse.results ?? [], "text");
          setResults(baseResults);
          setIsSearching(false);
          prefetchResultDetails(baseResults);
        } catch {
          if (searchRequestIdRef.current !== requestId) {
            return;
          }
          useSemanticAsPrimary = true;
        }
      }

      if (!useSemanticAsPrimary) {
        setIsLoadingRelated(true);
      }

      try {
        const semanticResponse = await searchRecipesClient(query, SEARCH_LIMIT);
        if (searchRequestIdRef.current !== requestId) {
          return;
        }

        const semanticResults = toMatchSourceResults(
          semanticResponse.results ?? [],
          "semantic",
        );

        if (useSemanticAsPrimary) {
          searchCacheRef.current[query] = {
            baseResults: semanticResults,
            relatedResults: [],
          };

          setResults(semanticResults);
          setRelatedResults([]);
          setIsSearching(false);
          setIsLoadingRelated(false);
          prefetchResultDetails(semanticResults);
          return;
        }

        const relatedOnly = getRelatedSemanticResults(baseResults, semanticResults);
        searchCacheRef.current[query] = {
          baseResults,
          relatedResults: relatedOnly,
        };

        setRelatedResults(relatedOnly);
        setIsLoadingRelated(false);
        if (relatedOnly.length > 0) {
          prefetchResultDetails(relatedOnly);
        }
      } catch (error) {
        if (searchRequestIdRef.current !== requestId) {
          return;
        }

        const semanticErrorMessage = getErrorMessage(error, "Search request failed.");
        setIsLoadingRelated(false);

        if (!useSemanticAsPrimary && baseResults.length > 0) {
          searchCacheRef.current[query] = {
            baseResults,
            relatedResults: [],
          };
          setIsSearching(false);
          return;
        }

        setResults([]);
        setRelatedResults([]);
        setIsSearching(false);
        setSearchError(semanticErrorMessage);
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
  const showLoadRelated =
    hasQuery && !searchError && relatedResults.length > 0 && !hasLoadedRelated;
  const showLoadingGrid = isSearching && !results.length;
  const showNoResults =
    !searchError && !isSearching && !results.length && !isLoadingRelated && !showLoadRelated;
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

  function handleLoadRelated() {
    if (!showLoadRelated) {
      return;
    }

    setResults((prev) => mergeBrowseResults(prev, relatedResults));
    setHasLoadedRelated(true);
  }

  async function handleLoadMore() {
    if (hasQuery || isLoadingMore || !defaultListHasMore || !defaultListNextCursor) {
      return;
    }

    setIsLoadingMore(true);
    setSearchError(null);

    try {
      const listResponse = await listRecipesClient(SEARCH_LIMIT, defaultListNextCursor);
      if (!isBrowseModeRef.current) {
        return;
      }
      const incomingResults = toBrowseResults(listResponse.recipes ?? []);
      const nextCursor = listResponse.next_cursor ?? null;
      const hasMore = Boolean(listResponse.has_more && nextCursor);

      setDefaultListNextCursor(nextCursor);
      setDefaultListHasMore(hasMore);
      setResults((prev) => {
        const merged = mergeBrowseResults(prev, incomingResults);
        defaultListCacheRef.current = {
          results: merged,
          nextCursor,
          hasMore,
        };
        return merged;
      });
      prefetchResultDetails(incomingResults);
    } catch (error) {
      if (!isBrowseModeRef.current) {
        return;
      }
      setSearchError(getErrorMessage(error, "Failed to load more recipes."));
    } finally {
      setIsLoadingMore(false);
    }
  }

  return {
    queryFromUrl,
    queryInput,
    results,
    relatedResultCount: relatedResults.length,
    searchError,
    isSearching,
    isLoadingRelated,
    showLoadRelated,
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
    handleLoadRelated,
    handleLoadMore,
    openRecipeModal,
    closeRecipeModal,
  };
}
