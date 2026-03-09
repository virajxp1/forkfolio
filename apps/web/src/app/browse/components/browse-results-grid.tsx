import { ArrowRight, Clock3, Users2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { RecipeRecord, SearchRecipeResult } from "@/lib/forkfolio-types";

function recipeTitleFromResult(result: SearchRecipeResult): string {
  return result.name?.trim() || "Untitled recipe";
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

type BrowseResultsGridProps = {
  queryFromUrl: string;
  results: SearchRecipeResult[];
  searchError: string | null;
  showInitialPrompt: boolean;
  showLoadingGrid: boolean;
  showNoResults: boolean;
  recipeById: Record<string, RecipeRecord>;
  recipeLoadingById: Record<string, boolean>;
  onCardOpen: (recipeId: string) => void;
};

export function BrowseResultsGrid({
  queryFromUrl,
  results,
  searchError,
  showInitialPrompt,
  showLoadingGrid,
  showNoResults,
  recipeById,
  recipeLoadingById,
  onCardOpen,
}: BrowseResultsGridProps) {
  return (
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
  );
}
