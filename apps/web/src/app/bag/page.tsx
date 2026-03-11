"use client";

import Link from "next/link";
import { ArrowLeft, Loader2, ShoppingBag, Trash2 } from "lucide-react";
import { useMemo, useRef, useState } from "react";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { useGroceryBag } from "@/components/grocery-bag-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { CreateGroceryListResponse } from "@/lib/forkfolio-types";

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

async function createGroceryListClient(
  recipeIds: string[],
): Promise<CreateGroceryListResponse> {
  const response = await fetch("/api/recipes/grocery-list", {
    method: "POST",
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      recipe_ids: recipeIds,
    }),
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

  return (await response.json()) as CreateGroceryListResponse;
}

export default function GroceryBagPage() {
  const { items, itemCount, removeRecipe, clearBag } = useGroceryBag();
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [generatedList, setGeneratedList] = useState<CreateGroceryListResponse | null>(
    null,
  );
  const generationRequestIdRef = useRef(0);

  const recipeIds = useMemo(() => items.map((item) => item.id), [items]);
  const hasItems = itemCount > 0;

  async function onGenerateGroceryList() {
    if (!hasItems) {
      setErrorMessage("Add at least one recipe to build a grocery list.");
      return;
    }

    const requestId = generationRequestIdRef.current + 1;
    generationRequestIdRef.current = requestId;
    const requestRecipeIds = [...recipeIds];

    setIsGenerating(true);
    setErrorMessage(null);

    try {
      const response = await createGroceryListClient(requestRecipeIds);
      if (generationRequestIdRef.current !== requestId) {
        return;
      }
      setGeneratedList(response);
    } catch (error) {
      if (generationRequestIdRef.current !== requestId) {
        return;
      }
      setGeneratedList(null);
      setErrorMessage(getErrorMessage(error, "Failed to generate grocery list."));
    } finally {
      if (generationRequestIdRef.current === requestId) {
        setIsGenerating(false);
      }
    }
  }

  return (
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <Button asChild variant="ghost" className="mb-4">
          <Link href="/browse">
            <ArrowLeft className="size-4" />
            Back to Browse
          </Link>
        </Button>

        <section className="rounded-[2rem] border border-border/70 bg-card/35 px-6 py-10 sm:px-10">
          <div className="mx-auto max-w-5xl space-y-6">
            <div className="space-y-3">
              <Badge variant="secondary" className="rounded-full px-3 py-0.5 text-xs">
                Grocery Bag
              </Badge>
              <h1 className="font-display text-5xl tracking-tight sm:text-6xl">
                Bag then build list
              </h1>
              <p className="text-lg text-muted-foreground">
                Add recipes as you browse, then generate one combined grocery list.
              </p>
            </div>

            <Card className="border-border/80 bg-background/85">
              <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3">
                <div>
                  <CardTitle className="font-display text-3xl">Selected Recipes</CardTitle>
                  <CardDescription>
                    {itemCount} recipe{itemCount === 1 ? "" : "s"} in bag
                  </CardDescription>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    generationRequestIdRef.current += 1;
                    setIsGenerating(false);
                    clearBag();
                    setGeneratedList(null);
                    setErrorMessage(null);
                  }}
                  disabled={!hasItems}
                >
                  <Trash2 className="size-4" />
                  Clear Bag
                </Button>
              </CardHeader>

              <CardContent className="space-y-3">
                {!hasItems ? (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Your bag is empty</CardTitle>
                      <CardDescription>
                        Open a recipe and use Add to Bag to start building your list.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Button asChild size="sm" variant="secondary">
                        <Link href="/browse">
                          <ShoppingBag className="size-4" />
                          Browse Recipes
                        </Link>
                      </Button>
                    </CardContent>
                  </Card>
                ) : (
                  items.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border/70 px-3 py-3"
                    >
                      <div className="min-w-0 space-y-1">
                        <p className="truncate font-medium text-foreground">
                          {item.title || "Untitled recipe"}
                        </p>
                        <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
                          {item.total_time ? (
                            <Badge variant="outline">{item.total_time}</Badge>
                          ) : null}
                          {item.servings ? <Badge variant="outline">{item.servings}</Badge> : null}
                        </div>
                      </div>

                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          generationRequestIdRef.current += 1;
                          setIsGenerating(false);
                          removeRecipe(item.id);
                          setGeneratedList(null);
                          setErrorMessage(null);
                        }}
                      >
                        Remove
                      </Button>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card className="border-border/80 bg-background/85">
              <CardHeader>
                <CardTitle className="font-display text-3xl">Build Grocery List</CardTitle>
                <CardDescription>
                  Generate one grocery list from all recipes in your bag.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  type="button"
                  onClick={() => {
                    void onGenerateGroceryList();
                  }}
                  disabled={isGenerating || !hasItems}
                >
                  {isGenerating ? <Loader2 className="size-4 animate-spin" /> : null}
                  {isGenerating ? "Generating..." : "Generate Grocery List"}
                </Button>

                {errorMessage ? (
                  <Card className="border-destructive/35 bg-destructive/5">
                    <CardHeader>
                      <CardTitle className="text-base">List generation failed</CardTitle>
                      <CardDescription>{errorMessage}</CardDescription>
                    </CardHeader>
                  </Card>
                ) : null}
              </CardContent>
            </Card>

            {generatedList ? (
              <Card className="border-primary/30 bg-primary/5">
                <CardHeader>
                  <CardTitle className="font-display text-3xl">Your Grocery List</CardTitle>
                  <CardDescription>
                    {generatedList.count} ingredient
                    {generatedList.count === 1 ? "" : "s"} from {generatedList.recipe_ids.length}{" "}
                    recipe{generatedList.recipe_ids.length === 1 ? "" : "s"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {generatedList.ingredients.map((ingredient, index) => (
                      <li
                        key={`${ingredient}-${index}`}
                        className="rounded-lg border border-border/70 bg-background/80 px-3 py-2"
                      >
                        {ingredient}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ) : null}
          </div>
        </section>
      </main>
    </div>
  );
}
