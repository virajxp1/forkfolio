"use client";

import Link from "next/link";
import {
  BookOpenText,
  Plus,
  Search,
  Sparkles,
  Users2,
} from "lucide-react";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { PageHero, PageMain, PageShell } from "@/components/page-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  RECENT_RECIPES_STORAGE_KEY,
  readRecentRecipes,
  type RecentRecipeItem,
} from "@/lib/recent-recipes";
import type {
  ListRecipeBooksResponse,
  RecipeBookRecord,
  SearchRecipeResult,
  SearchRecipesResponse,
} from "@/lib/forkfolio-types";

const QUICK_SEARCH_CHIPS = ["curry", "pasta", "high protein"];
const BOOK_SNAPSHOT_LIMIT = 3;
const SEARCH_SUGGEST_LIMIT = 5;
const MIN_SEARCH_LENGTH = 2;
const EMPTY_RECENT_RECIPES: RecentRecipeItem[] = [];
let cachedRecentRecipesRaw: string | null = null;
let cachedRecentRecipesSnapshot: RecentRecipeItem[] = EMPTY_RECENT_RECIPES;

const FEATURE_CARDS = [
  {
    id: "add",
    title: "Add Recipe",
    description: "Paste raw recipe text and convert it into clean, structured data.",
    href: "/recipes/new",
    cta: "Add New Recipe",
  },
  {
    id: "browse",
    title: "Browse & Search",
    description: "Use semantic search to find recipes by ingredients, cuisines, or meal type.",
    href: "/browse",
    cta: "Open Search",
  },
  {
    id: "books",
    title: "Recipe Books",
    description: "Group recipes into books and manage membership from any recipe page.",
    href: "/books",
    cta: "Open Books",
  },
] as const;

type ErrorPayload = {
  detail?: string;
  error?: string;
  message?: string;
};

type SearchSuggestion = {
  id: string;
  name: string;
};

async function readErrorPayload(response: Response): Promise<ErrorPayload | null> {
  try {
    return (await response.json()) as ErrorPayload;
  } catch {
    return null;
  }
}

async function browserFetch<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    throw new Error(payload?.detail ?? payload?.error ?? payload?.message ?? "Request failed.");
  }

  return (await response.json()) as T;
}

async function searchRecipesClient(query: string): Promise<SearchRecipesResponse> {
  const params = new URLSearchParams({
    query,
    limit: String(SEARCH_SUGGEST_LIMIT),
  });
  return browserFetch<SearchRecipesResponse>(`/api/search?${params.toString()}`);
}

async function listRecipeBooksSnapshotClient(): Promise<ListRecipeBooksResponse> {
  return browserFetch<ListRecipeBooksResponse>(
    `/api/recipe-books?limit=${BOOK_SNAPSHOT_LIMIT}`,
  );
}

function buildBrowseHref(query: string): string {
  const normalized = query.trim();
  if (!normalized) {
    return "/browse";
  }
  const params = new URLSearchParams({ q: normalized });
  return `/browse?${params.toString()}`;
}

function normalizeSearchResults(results: SearchRecipeResult[]): SearchSuggestion[] {
  return results
    .map((result) => {
      const id = result.id?.trim() ?? "";
      const name = result.name?.trim() ?? "";
      if (!id || !name) {
        return null;
      }
      return { id, name };
    })
    .filter((result): result is SearchSuggestion => result !== null);
}

function subscribeRecentRecipes(onStoreChange: () => void): () => void {
  const onStorage = (event: StorageEvent) => {
    if (
      event.storageArea === window.localStorage &&
      (event.key === RECENT_RECIPES_STORAGE_KEY || event.key === null)
    ) {
      onStoreChange();
    }
  };

  window.addEventListener("storage", onStorage);
  return () => {
    window.removeEventListener("storage", onStorage);
  };
}

function getRecentRecipesSnapshot(): RecentRecipeItem[] {
  const rawValue = window.localStorage.getItem(RECENT_RECIPES_STORAGE_KEY);
  if (rawValue === cachedRecentRecipesRaw) {
    return cachedRecentRecipesSnapshot;
  }

  cachedRecentRecipesRaw = rawValue;
  cachedRecentRecipesSnapshot = readRecentRecipes(window.localStorage);
  return cachedRecentRecipesSnapshot;
}

function getRecentRecipesServerSnapshot(): RecentRecipeItem[] {
  return EMPTY_RECENT_RECIPES;
}

export default function HomePage() {
  const router = useRouter();
  const [searchInput, setSearchInput] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);

  const recentRecipes = useSyncExternalStore(
    subscribeRecentRecipes,
    getRecentRecipesSnapshot,
    getRecentRecipesServerSnapshot,
  );
  const [recipeBooks, setRecipeBooks] = useState<RecipeBookRecord[]>([]);
  const [bookSnapshotError, setBookSnapshotError] = useState<string | null>(null);

  const normalizedSearchInput = searchInput.trim();
  const hasRecentRecipes = recentRecipes.length > 0;
  const canShowQuickResults = normalizedSearchInput.length >= MIN_SEARCH_LENGTH;
  const visibleSuggestions = canShowQuickResults ? suggestions : [];
  const visibleSearchError = canShowQuickResults ? searchError : null;
  const visibleSearching = canShowQuickResults ? isSearching : false;

  useEffect(() => {
    let canceled = false;

    void listRecipeBooksSnapshotClient()
      .then((response) => {
        if (canceled) {
          return;
        }
        setRecipeBooks(response.recipe_books ?? []);
        setBookSnapshotError(null);
      })
      .catch((error) => {
        if (canceled) {
          return;
        }
        setRecipeBooks([]);
        setBookSnapshotError(error instanceof Error ? error.message : "Failed to load books.");
      });

    return () => {
      canceled = true;
    };
  }, []);

  useEffect(() => {
    if (!canShowQuickResults) {
      return;
    }

    let canceled = false;
    const timeoutId = window.setTimeout(() => {
      setIsSearching(true);
      setSearchError(null);

      void searchRecipesClient(normalizedSearchInput)
        .then((response) => {
          if (canceled) {
            return;
          }
          setSuggestions(normalizeSearchResults(response.results ?? []));
        })
        .catch((error) => {
          if (canceled) {
            return;
          }
          setSuggestions([]);
          setSearchError(error instanceof Error ? error.message : "Search failed.");
        })
        .finally(() => {
          if (!canceled) {
            setIsSearching(false);
          }
        });
    }, 250);

    return () => {
      canceled = true;
      window.clearTimeout(timeoutId);
    };
  }, [canShowQuickResults, normalizedSearchInput]);

  const heroTitle = useMemo(() => {
    if (hasRecentRecipes) {
      return "Welcome back to your kitchen.";
    }
    return "Capture, find, and organize every recipe.";
  }, [hasRecentRecipes]);

  return (
    <PageShell>
      <ForkfolioHeader />

      <PageMain className="space-y-10 ff-animate-enter">
        <PageHero
          badge={hasRecentRecipes ? "Welcome Back" : "Home"}
          title={heroTitle}
          description="Capture recipes in seconds, search semantically, and organize everything into books that make cooking faster."
          actions={(
            <div className="grid w-full grid-cols-1 gap-3 sm:grid-cols-3">
              <Button asChild size="lg" className="h-12 rounded-full text-base font-semibold sm:h-14 sm:text-lg">
                <Link href="/recipes/new">
                  <Plus className="size-5" />
                  Add Recipe
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="secondary"
                className="h-12 rounded-full border border-border/70 bg-background/72 text-base font-semibold sm:h-14 sm:text-lg"
              >
                <Link href="/browse">
                  <Search className="size-5" />
                  Browse
                </Link>
              </Button>
              <Button
                asChild
                size="lg"
                variant="secondary"
                className="h-12 rounded-full border border-border/70 bg-background/72 text-base font-semibold sm:h-14 sm:text-lg"
              >
                <Link href="/books">
                  <BookOpenText className="size-5" />
                  Recipe Books
                </Link>
              </Button>
            </div>
          )}
        >
          <Card className="border-border/80 bg-background/88 shadow-none">
            <CardHeader>
              <CardTitle className="font-display text-3xl tracking-tight">
                Find recipes instantly
              </CardTitle>
              <CardDescription>
                Start typing to get quick suggestions, or jump to full browse search.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <form
                className="flex flex-col gap-3 sm:flex-row"
                onSubmit={(event) => {
                  event.preventDefault();
                  router.push(buildBrowseHref(searchInput));
                }}
              >
                <Input
                  type="search"
                  value={searchInput}
                  onChange={(event) => setSearchInput(event.target.value)}
                  placeholder="Search by dish, ingredient, or style"
                  className="h-11 border-border/80 bg-background/80 text-base"
                />
                <Button type="submit" variant="outline" className="h-11">
                  <Search className="size-4" />
                  Search
                </Button>
              </form>

              <div className="flex flex-wrap gap-2">
                {QUICK_SEARCH_CHIPS.map((chip) => (
                  <Button key={chip} asChild size="sm" variant="secondary" className="rounded-full">
                    <Link href={buildBrowseHref(chip)}>{chip}</Link>
                  </Button>
                ))}
              </div>

              {canShowQuickResults ? (
                <div className="space-y-2 rounded-xl border border-border/70 bg-background/74 px-4 py-3">
                  <p className="text-sm font-semibold text-foreground/90">Quick Results</p>
                  {visibleSearching ? (
                    <p className="text-sm text-muted-foreground">Searching...</p>
                  ) : visibleSearchError ? (
                    <p className="text-sm text-destructive">{visibleSearchError}</p>
                  ) : visibleSuggestions.length ? (
                    visibleSuggestions.map((suggestion) => (
                      <Button
                        key={suggestion.id}
                        asChild
                        variant="ghost"
                        className="h-9 w-full justify-start rounded-lg"
                      >
                        <Link href={`/recipes/${suggestion.id}`}>{suggestion.name}</Link>
                      </Button>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No quick matches yet.</p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Type at least {MIN_SEARCH_LENGTH} characters to show quick matches.
                </p>
              )}
            </CardContent>
          </Card>

          <div className="flex flex-wrap gap-2">
            <Badge variant="outline" className="rounded-full bg-background/65 px-3 py-1 text-xs">
              {recentRecipes.length} recent recipe{recentRecipes.length === 1 ? "" : "s"}
            </Badge>
            <Badge variant="outline" className="rounded-full bg-background/65 px-3 py-1 text-xs">
              {recipeBooks.length} book{recipeBooks.length === 1 ? "" : "s"} loaded
            </Badge>
          </div>
        </PageHero>

        <section className="grid grid-cols-1 gap-5 ff-animate-enter-delayed lg:grid-cols-[1.4fr_1fr]">
          <Card className="border-border/80 bg-background/80 shadow-none">
            <CardHeader>
              <CardTitle className="font-display text-3xl tracking-tight">
                {hasRecentRecipes ? "Continue where you left off" : "No recent recipes yet"}
              </CardTitle>
              <CardDescription>
                {hasRecentRecipes
                  ? "Recent recipes open in one click."
                  : "Open a recipe once and it will appear here for quick return access."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {hasRecentRecipes ? (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {recentRecipes.map((recipe) => (
                    <article
                      key={recipe.id}
                      className="space-y-3 rounded-xl border border-border/70 bg-background/74 px-4 py-4"
                    >
                      <div className="space-y-1">
                        <h3 className="line-clamp-2 text-lg font-semibold">{recipe.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          Viewed {new Date(recipe.viewed_at).toLocaleDateString()}
                        </p>
                      </div>
                      <Button asChild size="sm" variant="outline">
                        <Link href={`/recipes/${recipe.id}`}>Open Recipe</Link>
                      </Button>
                    </article>
                  ))}
                </div>
              ) : (
                <Button asChild variant="outline">
                  <Link href="/browse">Browse Recipes</Link>
                </Button>
              )}
            </CardContent>
          </Card>

          <Card className="border-border/80 bg-background/80 shadow-none">
            <CardHeader>
              <CardTitle className="font-display text-3xl tracking-tight">
                Recipe Books Snapshot
              </CardTitle>
              <CardDescription>
                Your latest books and recipe counts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {bookSnapshotError ? (
                <p className="text-sm text-destructive">{bookSnapshotError}</p>
              ) : recipeBooks.length ? (
                recipeBooks.map((book) => (
                  <article
                    key={book.id}
                    className="space-y-1 rounded-xl border border-border/70 bg-background/74 px-4 py-3"
                  >
                    <h3 className="text-lg font-semibold">{book.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {book.recipe_count} recipe{book.recipe_count === 1 ? "" : "s"}
                    </p>
                  </article>
                ))
              ) : (
                <p className="text-sm text-muted-foreground">No books yet.</p>
              )}

              <Button asChild variant="outline" size="sm">
                <Link href="/books">Manage Books</Link>
              </Button>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-5 ff-animate-enter-delayed">
          <h2 className="font-display text-[clamp(2rem,3.2vw,2.8rem)] tracking-tight">
            What You Can Do
          </h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {FEATURE_CARDS.map((feature) => (
              <Card
                key={feature.id}
                className={cn(
                  "border-border/80 bg-background/80 shadow-none",
                  feature.id === "add" && "md:col-span-2 xl:col-span-1",
                )}
              >
                <CardHeader className="space-y-2">
                  <CardTitle className="font-display text-3xl tracking-tight">
                    {feature.title}
                  </CardTitle>
                  <CardDescription>{feature.description}</CardDescription>
                </CardHeader>
                <CardContent>
                  <Button asChild size="sm" variant="outline">
                    <Link href={feature.href}>
                      {feature.id === "browse" ? <Search className="size-4" /> : null}
                      {feature.id === "books" ? <Users2 className="size-4" /> : null}
                      {feature.id === "add" ? <Sparkles className="size-4" /> : null}
                      {feature.cta}
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </PageMain>
    </PageShell>
  );
}
