"use client";

import Link from "next/link";
import { BookOpenText, Loader2, Plus, RefreshCw } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { PageBackLink, PageHero, PageMain, PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import type {
  CreateRecipeBookResponse,
  GetRecipeBookStatsResponse,
  ListRecipeBooksResponse,
  RecipeBookRecord,
  RecipeBookStats,
} from "@/lib/forkfolio-types";

type ErrorPayload = {
  detail?: string;
  error?: string;
  message?: string;
};

const RECIPE_BOOKS_LIMIT = 200;

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

async function browserFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detail = payload?.detail ?? payload?.error ?? payload?.message ?? null;
    throw new BrowserApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

async function listRecipeBooksClient(
  limit = RECIPE_BOOKS_LIMIT,
): Promise<ListRecipeBooksResponse> {
  return browserFetch<ListRecipeBooksResponse>(`/api/recipe-books?limit=${limit}`);
}

async function getRecipeBookStatsClient(): Promise<GetRecipeBookStatsResponse> {
  return browserFetch<GetRecipeBookStatsResponse>("/api/recipe-books/stats");
}

async function createRecipeBookClient(
  name: string,
  description: string,
): Promise<CreateRecipeBookResponse> {
  return browserFetch<CreateRecipeBookResponse>("/api/recipe-books", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name,
      description,
    }),
  });
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <Card className="border-border/80 bg-background/82 shadow-none">
      <CardHeader className="space-y-1">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="font-display text-4xl tracking-tight">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}

function RecipeBookCard({ recipeBook }: { recipeBook: RecipeBookRecord }) {
  return (
    <Card className="border-border/80 bg-background/80 shadow-none transition hover:-translate-y-0.5 hover:shadow-sm">
      <CardHeader>
        <CardTitle className="font-display text-3xl leading-tight">
          {recipeBook.name}
        </CardTitle>
        <CardDescription>
          {recipeBook.recipe_count} recipe{recipeBook.recipe_count === 1 ? "" : "s"}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          {recipeBook.description?.trim() || "No description yet."}
        </p>

        <Button asChild size="sm" variant="outline">
          <Link href={`/books/${recipeBook.id}`}>
            Open Recipe Book
            <BookOpenText className="size-4" />
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}

export default function RecipeBooksPage() {
  const [recipeBooks, setRecipeBooks] = useState<RecipeBookRecord[]>([]);
  const [stats, setStats] = useState<RecipeBookStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createResult, setCreateResult] = useState<{
    created: boolean;
    id: string;
    name: string;
  } | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);

    try {
      const [listResponse, statsResponse] = await Promise.all([
        listRecipeBooksClient(RECIPE_BOOKS_LIMIT),
        getRecipeBookStatsClient(),
      ]);
      setRecipeBooks(listResponse.recipe_books ?? []);
      setStats(statsResponse.stats ?? null);
    } catch (error) {
      setLoadError(getErrorMessage(error, "Failed to load recipe books."));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const trimmedName = useMemo(() => name.trim(), [name]);
  const canCreate = trimmedName.length > 0;
  const totalRecipeBooks = stats?.total_recipe_books ?? recipeBooks.length;
  const isBookListTruncated = totalRecipeBooks > RECIPE_BOOKS_LIMIT;

  async function onCreateRecipeBook(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!canCreate) {
      setCreateError("Recipe book name is required.");
      return;
    }

    setIsCreating(true);
    setCreateError(null);
    setCreateResult(null);

    try {
      const response = await createRecipeBookClient(trimmedName, description.trim());
      setCreateResult({
        created: response.created,
        id: response.recipe_book.id,
        name: response.recipe_book.name,
      });
      setName("");
      setDescription("");
      await loadData();
    } catch (error) {
      setCreateError(getErrorMessage(error, "Failed to create recipe book."));
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <PageShell>
      <ForkfolioHeader />

      <PageMain className="space-y-10 ff-animate-enter">
        <PageBackLink href="/" label="Back to Home" />

        <PageHero
          badge="Recipe Books"
          title="Organize recipes into collections"
          description="Group recipes by cuisine, mood, season, or any style that helps you cook faster."
          contentClassName="max-w-5xl"
        >
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1.25fr_1fr]">
              <Card className="border-border/80 bg-background/82 shadow-none">
                <CardHeader>
                  <CardTitle className="font-display text-3xl">Create Recipe Book</CardTitle>
                  <CardDescription>
                    Creating an existing name returns the existing book.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <form className="space-y-4" onSubmit={onCreateRecipeBook}>
                    <div className="space-y-2">
                      <Label htmlFor="name">Name</Label>
                      <Input
                        id="name"
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Weeknight Dinners"
                        className="border-border/80 bg-background/80"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="description">Description (optional)</Label>
                      <Textarea
                        id="description"
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                        placeholder="Fast, high-protein meals for weekdays"
                        className="min-h-24 resize-y border-border/80 bg-background/80"
                      />
                    </div>

                    <Button type="submit" disabled={isCreating || !canCreate}>
                      {isCreating ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />}
                      {isCreating ? "Saving..." : "Create Recipe Book"}
                    </Button>
                  </form>

                  {createError ? (
                    <Card className="mt-4 border-destructive/35 bg-destructive/5">
                      <CardHeader>
                        <CardTitle className="text-base">Unable to create recipe book</CardTitle>
                        <CardDescription>{createError}</CardDescription>
                      </CardHeader>
                    </Card>
                  ) : null}

                  {createResult ? (
                    <Card className="mt-4 border-primary/30 bg-primary/5">
                      <CardHeader>
                        <CardTitle className="text-base">
                          {createResult.created ? "Recipe book created" : "Recipe book already exists"}
                        </CardTitle>
                        <CardDescription>{createResult.name}</CardDescription>
                      </CardHeader>
                      <CardContent>
                        <Button asChild size="sm" variant="outline">
                          <Link href={`/books/${createResult.id}`}>Open Recipe Book</Link>
                        </Button>
                      </CardContent>
                    </Card>
                  ) : null}
                </CardContent>
              </Card>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="font-display text-3xl tracking-tight">Stats</h2>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      void loadData();
                    }}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <RefreshCw className="size-4" />
                    )}
                    Refresh
                  </Button>
                </div>

                {isLoading ? (
                  <div className="space-y-3">
                    <Skeleton className="h-24 w-full bg-muted/85" />
                    <Skeleton className="h-24 w-full bg-muted/85" />
                    <Skeleton className="h-24 w-full bg-muted/85" />
                  </div>
                ) : (
                  <>
                    <StatCard
                      label="Total Recipe Books"
                      value={String(stats?.total_recipe_books ?? 0)}
                    />
                    <StatCard
                      label="Total Book Links"
                      value={String(stats?.total_recipe_book_links ?? 0)}
                    />
                    <StatCard
                      label="Average Recipes / Book"
                      value={String(stats?.avg_recipes_per_book ?? 0)}
                    />
                  </>
                )}
              </div>
            </div>
        </PageHero>

        <section className="space-y-5 ff-animate-enter-delayed">
          <h2 className="font-display text-3xl tracking-tight">Your Recipe Books</h2>

          {!isLoading && !loadError && isBookListTruncated ? (
            <Card className="border-border/80 bg-background/80 shadow-none">
              <CardHeader>
                <CardTitle className="text-base">
                  Showing first {RECIPE_BOOKS_LIMIT} recipe books
                </CardTitle>
                <CardDescription>
                  You currently have {totalRecipeBooks} recipe books. Additional books are
                  not shown in this view yet.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : null}

          {loadError ? (
            <Card className="border-destructive/35 bg-destructive/5">
              <CardHeader>
                <CardTitle>Unable to load recipe books</CardTitle>
                <CardDescription>{loadError}</CardDescription>
              </CardHeader>
            </Card>
          ) : null}

          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              <Skeleton className="h-52 w-full rounded-xl bg-muted/85" />
              <Skeleton className="h-52 w-full rounded-xl bg-muted/85" />
              <Skeleton className="h-52 w-full rounded-xl bg-muted/85" />
            </div>
          ) : null}

          {!isLoading && !loadError && !recipeBooks.length ? (
            <Card>
              <CardHeader>
                <CardTitle>No recipe books yet</CardTitle>
                <CardDescription>
                  Create your first recipe book to start organizing recipes.
                </CardDescription>
              </CardHeader>
            </Card>
          ) : null}

          {!isLoading && recipeBooks.length ? (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              {recipeBooks.map((recipeBook) => (
                <RecipeBookCard key={recipeBook.id} recipeBook={recipeBook} />
              ))}
            </div>
          ) : null}
        </section>
      </PageMain>
    </PageShell>
  );
}
