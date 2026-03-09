"use client";

import Link from "next/link";
import { BookOpenText, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type {
  AddRecipeToBookResponse,
  GetRecipeBooksForRecipeResponse,
  ListRecipeBooksResponse,
  RecipeBookRecord,
  RemoveRecipeFromBookResponse,
} from "@/lib/forkfolio-types";

type ErrorPayload = {
  detail?: string;
  error?: string;
  message?: string;
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

async function listRecipeBooksClient(): Promise<ListRecipeBooksResponse> {
  return browserFetch<ListRecipeBooksResponse>("/api/recipe-books?limit=200");
}

async function getRecipeBooksForRecipeClient(
  recipeId: string,
): Promise<GetRecipeBooksForRecipeResponse> {
  return browserFetch<GetRecipeBooksForRecipeResponse>(
    `/api/recipe-books/by-recipe/${encodeURIComponent(recipeId)}`,
  );
}

async function addRecipeToBookClient(
  recipeBookId: string,
  recipeId: string,
): Promise<AddRecipeToBookResponse> {
  return browserFetch<AddRecipeToBookResponse>(
    `/api/recipe-books/${encodeURIComponent(recipeBookId)}/recipes/${encodeURIComponent(recipeId)}`,
    {
      method: "PUT",
    },
  );
}

async function removeRecipeFromBookClient(
  recipeBookId: string,
  recipeId: string,
): Promise<RemoveRecipeFromBookResponse> {
  return browserFetch<RemoveRecipeFromBookResponse>(
    `/api/recipe-books/${encodeURIComponent(recipeBookId)}/recipes/${encodeURIComponent(recipeId)}`,
    {
      method: "DELETE",
    },
  );
}

export function RecipeBookMembership({ recipeId }: { recipeId: string }) {
  const [recipeBooks, setRecipeBooks] = useState<RecipeBookRecord[]>([]);
  const [memberBookIds, setMemberBookIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [mutationByBookId, setMutationByBookId] = useState<Record<string, boolean>>(
    {},
  );

  const loadRecipeBooks = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [allBooksResponse, membershipsResponse] = await Promise.all([
        listRecipeBooksClient(),
        getRecipeBooksForRecipeClient(recipeId),
      ]);

      const books = allBooksResponse.recipe_books ?? [];
      const memberships = membershipsResponse.recipe_books ?? [];

      setRecipeBooks(books);
      setMemberBookIds(new Set(memberships.map((book) => book.id)));
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to load recipe books."));
    } finally {
      setIsLoading(false);
    }
  }, [recipeId]);

  useEffect(() => {
    void loadRecipeBooks();
  }, [loadRecipeBooks]);

  const booksCount = useMemo(() => memberBookIds.size, [memberBookIds]);

  async function onToggleMembership(book: RecipeBookRecord) {
    const recipeBookId = book.id;
    const isMember = memberBookIds.has(recipeBookId);

    setMutationByBookId((prev) => ({ ...prev, [recipeBookId]: true }));
    setErrorMessage(null);

    try {
      if (isMember) {
        await removeRecipeFromBookClient(recipeBookId, recipeId);
      } else {
        await addRecipeToBookClient(recipeBookId, recipeId);
      }

      setMemberBookIds((prev) => {
        const next = new Set(prev);
        if (isMember) {
          next.delete(recipeBookId);
        } else {
          next.add(recipeBookId);
        }
        return next;
      });

      setRecipeBooks((prev) =>
        prev.map((existingBook) => {
          if (existingBook.id !== recipeBookId) {
            return existingBook;
          }

          const nextCount = isMember
            ? Math.max(0, existingBook.recipe_count - 1)
            : existingBook.recipe_count + 1;

          return {
            ...existingBook,
            recipe_count: nextCount,
          };
        }),
      );
    } catch (error) {
      setErrorMessage(
        getErrorMessage(error, "Failed to update recipe book membership."),
      );
    } finally {
      setMutationByBookId((prev) => {
        const next = { ...prev };
        delete next[recipeBookId];
        return next;
      });
    }
  }

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="font-display text-3xl">Recipe Books</CardTitle>
            <CardDescription>
              This recipe is in {booksCount} book{booksCount === 1 ? "" : "s"}.
            </CardDescription>
          </div>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              void loadRecipeBooks();
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
      </CardHeader>

      <CardContent className="space-y-3">
        {errorMessage ? (
          <Card className="border-destructive/35 bg-destructive/5">
            <CardHeader>
              <CardTitle className="text-base">Unable to load recipe books</CardTitle>
              <CardDescription>{errorMessage}</CardDescription>
            </CardHeader>
          </Card>
        ) : null}

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-11 w-full bg-muted/85" />
            <Skeleton className="h-11 w-full bg-muted/85" />
            <Skeleton className="h-11 w-full bg-muted/85" />
          </div>
        ) : null}

        {!isLoading && !recipeBooks.length ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">No recipe books yet</CardTitle>
              <CardDescription>
                Create your first recipe book to start organizing recipes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild size="sm" variant="secondary">
                <Link href="/books">
                  <BookOpenText className="size-4" />
                  Go to Recipe Books
                </Link>
              </Button>
            </CardContent>
          </Card>
        ) : null}

        {!isLoading && recipeBooks.length
          ? recipeBooks.map((book) => {
              const isMember = memberBookIds.has(book.id);
              const isMutating = Boolean(mutationByBookId[book.id]);

              return (
                <div
                  key={book.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-3"
                >
                  <div className="min-w-0 space-y-1">
                    <Link
                      href={`/books/${book.id}`}
                      className="block truncate font-medium text-foreground hover:text-primary"
                    >
                      {book.name}
                    </Link>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <span>{book.recipe_count} recipe{book.recipe_count === 1 ? "" : "s"}</span>
                      {isMember ? <Badge variant="secondary">In Book</Badge> : null}
                    </div>
                  </div>

                  <Button
                    type="button"
                    size="sm"
                    variant={isMember ? "outline" : "secondary"}
                    disabled={isMutating}
                    onClick={() => {
                      void onToggleMembership(book);
                    }}
                  >
                    {isMutating ? <Loader2 className="size-4 animate-spin" /> : null}
                    {isMember ? "Remove" : "Add"}
                  </Button>
                </div>
              );
            })
          : null}
      </CardContent>
    </Card>
  );
}
