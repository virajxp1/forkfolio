"use client";

import {
  ArrowLeft,
  ArrowRight,
  Clock3,
  ExternalLink,
  Search,
  Users2,
  X,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  GetRecipeResponse,
  RecipeRecord,
  SearchRecipeResult,
  SearchRecipesResponse,
} from "@/lib/forkfolio-types";

const SEARCH_LIMIT = 12;
const MIN_QUERY_LENGTH = 2;

type ErrorPayload = {
  detail?: string;
  error?: string;
};

class BrowserApiError extends Error {
  status: number;

  detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = "BrowserApiError";
    this.status = status;
    this.detail = detail;
  }
}

function normalizeParam(rawParam: string | null): string {
  return (rawParam ?? "").trim();
}

function buildBrowseHref(query: string, recipeId?: string): string {
  const params = new URLSearchParams();
  if (query) {
    params.set("q", query);
  }
  if (recipeId) {
    params.set("recipe", recipeId);
  }

  const serialized = params.toString();
  return serialized ? `/browse?${serialized}` : "/browse";
}

function recipeTitleFromResult(result: SearchRecipeResult): string {
  return result.name?.trim() || "Untitled recipe";
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof BrowserApiError) {
    return error.detail ?? error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

async function readErrorPayload(response: Response): Promise<ErrorPayload | null> {
  try {
    return (await response.json()) as ErrorPayload;
  } catch {
    return null;
  }
}

async function browserFetch<T>(pathWithQuery: string): Promise<T> {
  const path = pathWithQuery.startsWith("/") ? pathWithQuery : `/${pathWithQuery}`;
  const response = await fetch(path, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detail = payload?.detail ?? payload?.error ?? null;
    throw new BrowserApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

async function searchRecipesClient(
  query: string,
  limit = SEARCH_LIMIT,
): Promise<SearchRecipesResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  return browserFetch<SearchRecipesResponse>(`/api/search?${params.toString()}`);
}

async function getRecipeClient(recipeId: string): Promise<GetRecipeResponse> {
  return browserFetch<GetRecipeResponse>(`/api/recipes/${recipeId}`);
}

function ResultCardLoading() {
  return (
    <Card className="h-full border-border/80">
      <CardHeader className="space-y-4">
        <Skeleton className="h-8 w-2/3 rounded-lg bg-muted/85" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-24 rounded-full bg-muted/85" />
          <Skeleton className="h-6 w-20 rounded-full bg-muted/85" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-3 w-16 rounded bg-muted/85" />
        <Skeleton className="h-4 w-11/12 bg-muted/85" />
        <Skeleton className="h-4 w-10/12 bg-muted/85" />
        <Skeleton className="h-4 w-9/12 bg-muted/85" />
        <Skeleton className="mt-2 h-4 w-28 bg-muted/85" />
      </CardContent>
    </Card>
  );
}

function SearchCard({
  result,
  recipe,
  isDetailsLoading,
  onOpen,
}: {
  result: SearchRecipeResult;
  recipe?: RecipeRecord;
  isDetailsLoading: boolean;
  onOpen: (recipeId: string) => void;
}) {
  const title = recipeTitleFromResult(result);
  const recipeId = result.id;
  const ingredients = recipe?.ingredients?.slice(0, 3) ?? [];
  const canOpen = Boolean(recipeId);

  return (
    <button
      type="button"
      onClick={() => {
        if (recipeId) {
          onOpen(recipeId);
        }
      }}
      disabled={!canOpen}
      className={`block h-full w-full text-left ${canOpen ? "" : "pointer-events-none opacity-60"}`}
      aria-label={`Open ${title}`}
    >
      <Card className="h-full border-border/80 transition hover:-translate-y-0.5 hover:shadow-md">
        <CardHeader className="gap-3">
          <CardTitle className="font-display text-2xl tracking-tight">{title}</CardTitle>

          <CardDescription className="flex min-h-6 flex-wrap items-center gap-2 text-sm">
            {recipe ? (
              <>
                {recipe.total_time ? (
                  <Badge variant="outline" className="gap-1.5">
                    <Clock3 className="size-3" />
                    {recipe.total_time}
                  </Badge>
                ) : null}
                {recipe.servings ? (
                  <Badge variant="outline" className="gap-1.5">
                    <Users2 className="size-3" />
                    {recipe.servings}
                  </Badge>
                ) : null}
                {!recipe.total_time && !recipe.servings ? (
                  <span className="text-muted-foreground">Metadata available</span>
                ) : null}
              </>
            ) : isDetailsLoading ? (
              <>
                <Skeleton className="h-6 w-20 rounded-full bg-muted/85" />
                <Skeleton className="h-6 w-16 rounded-full bg-muted/85" />
              </>
            ) : (
              <span className="text-muted-foreground">Metadata unavailable</span>
            )}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-3">
          <div className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Preview
          </div>

          {recipe ? (
            ingredients.length ? (
              <ul className="space-y-1">
                {ingredients.map((ingredient) => (
                  <li
                    key={`${result.id}-${ingredient}`}
                    className="truncate text-sm text-foreground/85"
                    title={ingredient}
                  >
                    • {ingredient}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                No ingredient preview available. Open the recipe for full details.
              </p>
            )
          ) : isDetailsLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-11/12 bg-muted/85" />
              <Skeleton className="h-4 w-10/12 bg-muted/85" />
              <Skeleton className="h-4 w-9/12 bg-muted/85" />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Preview unavailable right now. Open the recipe for full details.
            </p>
          )}

          <div className="inline-flex items-center gap-1.5 text-sm font-medium text-primary">
            Open recipe
            <ArrowRight className="size-4" />
          </div>
        </CardContent>
      </Card>
    </button>
  );
}

function RecipeModal({
  recipeId,
  recipe,
  isLoading,
  error,
  onClose,
}: {
  recipeId: string;
  recipe: RecipeRecord | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 p-4 backdrop-blur-sm">
      <button
        type="button"
        className="absolute inset-0"
        onClick={onClose}
        aria-label="Close recipe details"
      />

      <Card
        role="dialog"
        aria-modal="true"
        className="relative z-10 w-full max-w-5xl overflow-hidden border-border/80 bg-background shadow-xl"
      >
        <div className="flex items-start justify-between gap-4 border-b border-border/70 px-6 py-5">
          <div className="space-y-2">
            {recipe ? (
              <h3 className="font-display text-4xl leading-tight tracking-tight text-primary sm:text-5xl">
                {recipe.title || "Recipe"}
              </h3>
            ) : isLoading ? (
              <Skeleton className="h-12 w-72 bg-muted/85" />
            ) : (
              <h3 className="font-display text-4xl leading-tight tracking-tight text-primary sm:text-5xl">
                Recipe
              </h3>
            )}

            {recipe ? (
              <div className="flex flex-wrap gap-2">
                {recipe.total_time ? (
                  <Badge variant="secondary" className="gap-1.5">
                    <Clock3 className="size-3.5" />
                    {recipe.total_time}
                  </Badge>
                ) : null}
                {recipe.servings ? (
                  <Badge variant="secondary" className="gap-1.5">
                    <Users2 className="size-3.5" />
                    {recipe.servings}
                  </Badge>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className="flex items-center gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href={`/recipes/${recipeId}`}>
                Open Full Page
                <ExternalLink className="size-4" />
              </Link>
            </Button>

            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className="rounded-full"
              onClick={onClose}
              aria-label="Close recipe details"
            >
              <X className="size-4" />
            </Button>
          </div>
        </div>

        <div className="max-h-[75vh] overflow-y-auto px-6 py-5">
          {error ? (
            <Card className="border-destructive/35 bg-destructive/5">
              <CardHeader>
                <CardTitle>Unable to load recipe</CardTitle>
                <CardDescription>{error}</CardDescription>
              </CardHeader>
            </Card>
          ) : null}

          {!error && isLoading && !recipe ? (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_1.3fr]">
              <Card>
                <CardHeader>
                  <Skeleton className="h-10 w-40 bg-muted/85" />
                  <Skeleton className="h-5 w-24 bg-muted/85" />
                </CardHeader>
                <CardContent className="space-y-2">
                  <Skeleton className="h-4 w-11/12 bg-muted/85" />
                  <Skeleton className="h-4 w-10/12 bg-muted/85" />
                  <Skeleton className="h-4 w-9/12 bg-muted/85" />
                  <Skeleton className="h-4 w-8/12 bg-muted/85" />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <Skeleton className="h-10 w-44 bg-muted/85" />
                  <Skeleton className="h-5 w-24 bg-muted/85" />
                </CardHeader>
                <CardContent className="space-y-3">
                  <Skeleton className="h-6 w-full bg-muted/85" />
                  <Skeleton className="h-6 w-[96%] bg-muted/85" />
                  <Skeleton className="h-6 w-[92%] bg-muted/85" />
                  <Skeleton className="h-6 w-[94%] bg-muted/85" />
                </CardContent>
              </Card>
            </div>
          ) : null}

          {recipe ? (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_1.3fr]">
              <Card>
                <CardHeader>
                  <CardTitle className="font-display text-3xl">Ingredients</CardTitle>
                  <CardDescription>
                    {recipe.ingredients.length} item
                    {recipe.ingredients.length === 1 ? "" : "s"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {recipe.ingredients.map((ingredient, index) => (
                      <li key={`${ingredient}-${index}`} className="text-foreground/90">
                        • {ingredient}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="font-display text-3xl">Instructions</CardTitle>
                  <CardDescription>
                    {recipe.instructions.length} step
                    {recipe.instructions.length === 1 ? "" : "s"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ol className="space-y-3">
                    {recipe.instructions.map((instruction, index) => (
                      <li
                        key={`${instruction}-${index}`}
                        className="flex items-start gap-3"
                      >
                        <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                          {index + 1}
                        </span>
                        <p className="pt-0.5 text-foreground/90">{instruction}</p>
                      </li>
                    ))}
                  </ol>
                </CardContent>
              </Card>
            </div>
          ) : null}
        </div>
      </Card>
    </div>
  );
}

export default function BrowsePage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const queryFromUrl = normalizeParam(searchParams.get("q"));
  const recipeIdFromUrl = normalizeParam(searchParams.get("recipe"));

  const [queryInput, setQueryInput] = useState(queryFromUrl);
  const [results, setResults] = useState<SearchRecipeResult[]>([]);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const [recipeById, setRecipeById] = useState<Record<string, RecipeRecord>>({});
  const [recipeLoadingById, setRecipeLoadingById] = useState<Record<string, boolean>>(
    {},
  );

  const [selectedRecipeLoading, setSelectedRecipeLoading] = useState(false);
  const [selectedRecipeError, setSelectedRecipeError] = useState<string | null>(null);

  const searchCacheRef = useRef<Record<string, SearchRecipeResult[]>>({});
  const recipeCacheRef = useRef<Record<string, RecipeRecord>>({});
  const inFlightRecipeRef = useRef<Record<string, Promise<RecipeRecord>>>({});
  const searchRequestIdRef = useRef(0);

  const setBrowseUrl = useCallback(
    (
      nextQuery: string,
      nextRecipeId?: string,
      navigation: "push" | "replace" = "push",
    ) => {
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
        setResults([]);
        setSearchError(null);
        setIsSearching(false);
        return;
      }

      if (query.length < MIN_QUERY_LENGTH) {
        setResults([]);
        setSearchError("Search query must be at least 2 characters.");
        setIsSearching(false);
        return;
      }

      const cachedResults = searchCacheRef.current[query];
      if (cachedResults) {
        setResults(cachedResults);
        setSearchError(null);
        setIsSearching(false);
        prefetchResultDetails(cachedResults);
        return;
      }

      setIsSearching(true);
      setSearchError(null);
      setResults([]);

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
          setSelectedRecipeError(
            getErrorMessage(error, "Failed to load recipe details."),
          );
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

  const hasModal = Boolean(recipeIdFromUrl);

  function onSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuery = queryInput.trim();

    if (!normalizedQuery) {
      setBrowseUrl("", undefined, "replace");
      return;
    }

    setBrowseUrl(normalizedQuery, undefined, "push");
  }

  function onCardOpen(recipeId: string) {
    setBrowseUrl(queryFromUrl, recipeId, "push");
  }

  function onModalClose() {
    setBrowseUrl(queryFromUrl, undefined, "replace");
  }

  const showInitialPrompt = !queryFromUrl && !searchError;
  const showLoadingGrid = queryFromUrl && isSearching && !results.length;
  const showNoResults = queryFromUrl && !searchError && !isSearching && !results.length;

  return (
    <div className="min-h-screen">
      <div className={hasModal ? "pointer-events-none select-none blur-[3px]" : ""}>
        <ForkfolioHeader />

        <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
          <Button asChild variant="ghost" className="mb-4">
            <Link href="/">
              <ArrowLeft className="size-4" />
              Back to Home
            </Link>
          </Button>

          <section className="rounded-[2rem] border border-border/70 bg-card/35 px-6 py-10 sm:px-10">
            <div className="mx-auto max-w-4xl space-y-6">
              <div className="space-y-2">
                <Badge variant="secondary" className="rounded-full px-3 py-0.5 text-xs">
                  Browse Recipes
                </Badge>
                <h1 className="font-display text-5xl tracking-tight sm:text-6xl">
                  Find anything instantly
                </h1>
                <p className="text-lg text-muted-foreground">
                  Search your collection and open any result to view full recipe details.
                </p>
              </div>

              <form onSubmit={onSearchSubmit} className="flex flex-col gap-3 sm:flex-row">
                <div className="relative flex-1">
                  <Search className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    type="search"
                    name="q"
                    value={queryInput}
                    onChange={(event) => {
                      const nextQuery = event.target.value;
                      setQueryInput(nextQuery);

                      if (nextQuery.trim() === "" && (queryFromUrl || recipeIdFromUrl)) {
                        setBrowseUrl("", undefined, "replace");
                      }
                    }}
                    placeholder="Search recipes... e.g. 'creamy pasta' or 'quick breakfast'"
                    className="h-14 rounded-2xl border-border/90 bg-background pl-11 text-base"
                  />
                </div>
                <Button
                  type="submit"
                  size="lg"
                  className="h-14 rounded-2xl px-8 text-lg"
                  disabled={isSearching}
                >
                  Search
                </Button>
              </form>
            </div>
          </section>

          <section className="mt-10 space-y-5">
            <h2 className="font-display text-3xl tracking-tight">
              {queryFromUrl ? `Results for "${queryFromUrl}"` : "Search Results"}
            </h2>

            {searchError ? (
              <Card className="border-destructive/35 bg-destructive/5">
                <CardHeader>
                  <CardTitle>Search Error</CardTitle>
                  <CardDescription>{searchError}</CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {showInitialPrompt ? (
              <Card>
                <CardHeader>
                  <CardTitle>Start with a query</CardTitle>
                  <CardDescription>
                    Try a dish, cuisine, ingredient, or meal type.
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {showLoadingGrid ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                <ResultCardLoading />
                <ResultCardLoading />
                <ResultCardLoading />
                <ResultCardLoading />
                <ResultCardLoading />
                <ResultCardLoading />
              </div>
            ) : null}

            {showNoResults ? (
              <Card>
                <CardHeader>
                  <CardTitle>No recipes found</CardTitle>
                  <CardDescription>
                    Try different keywords or a broader phrase.
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {queryFromUrl && results.length ? (
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {results.map((result) => {
                  const recipeId = result.id ?? "";
                  const recipe = recipeId ? recipeById[recipeId] : undefined;
                  const isDetailsLoading = recipeId ? Boolean(recipeLoadingById[recipeId]) : false;

                  return (
                    <SearchCard
                      key={result.id ?? `${result.name}-${result.distance}`}
                      result={result}
                      recipe={recipe}
                      isDetailsLoading={isDetailsLoading}
                      onOpen={onCardOpen}
                    />
                  );
                })}
              </div>
            ) : null}
          </section>
        </main>
      </div>

      {hasModal ? (
        <RecipeModal
          recipeId={recipeIdFromUrl}
          recipe={selectedRecipe}
          isLoading={selectedRecipeLoading && !selectedRecipe}
          error={selectedRecipeError}
          onClose={onModalClose}
        />
      ) : null}
    </div>
  );
}
