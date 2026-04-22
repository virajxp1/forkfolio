import { ArrowRight } from "lucide-react";

import { RecipeBagToggleButton } from "@/components/recipe-bag-toggle-button";
import { RecipeMetadataBadges } from "@/components/recipe-metadata-badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { RecipeRecord } from "@/lib/forkfolio-types";

import type { BrowseSearchResult } from "../use-browse-data";

function recipeTitleFromResult(result: BrowseSearchResult): string {
  return result.name?.trim() || "Untitled recipe";
}

function ResultCardLoading() {
  return (
    <Card className="h-full border-border/80 bg-background/80 shadow-none">
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
  result: BrowseSearchResult;
  recipe?: RecipeRecord;
  isDetailsLoading: boolean;
  onOpen: (recipeId: string) => void;
}) {
  const title = recipeTitleFromResult(result);
  const recipeId = result.id;
  const ingredients = recipe?.ingredients?.slice(0, 3) ?? [];
  const canOpen = Boolean(recipeId);
  const hasRecipeMetadata = Boolean(
    recipe?.total_time?.trim() ||
      recipe?.servings?.trim() ||
      typeof recipe?.is_public === "boolean",
  );

  return (
    <Card
      className={`relative h-full border-border/80 bg-background/80 shadow-none transition ${
        canOpen ? "hover:-translate-y-0.5 hover:shadow-md" : "opacity-60"
      }`}
    >
      <Button
        type="button"
        variant="ghost"
        onClick={() => {
          if (recipeId) {
            onOpen(recipeId);
          }
        }}
        disabled={!canOpen}
        aria-label={`Open ${title}`}
        className="absolute inset-0 z-10 h-full w-full rounded-xl border-0 p-0 hover:bg-transparent"
      >
        <span className="sr-only">Open {title}</span>
      </Button>

      <CardHeader className="gap-3">
        <CardTitle
          className="line-clamp-2 break-words font-display text-2xl tracking-tight"
          title={title}
        >
          {title}
        </CardTitle>

        <CardDescription className="flex min-h-6 min-w-0 flex-wrap items-center gap-2 text-sm">
          {result.matchSource === "semantic" ? (
            <Badge variant="secondary">Related recipe</Badge>
          ) : null}

          {recipe ? (
            hasRecipeMetadata ? (
              <RecipeMetadataBadges
                servings={recipe.servings}
                totalTime={recipe.total_time}
                isPublic={recipe.is_public}
              />
            ) : (
              <span className="text-muted-foreground">No time or serving info yet.</span>
            )
          ) : isDetailsLoading ? (
            <>
              <Skeleton className="h-6 w-20 rounded-full bg-muted/85" />
              <Skeleton className="h-6 w-16 rounded-full bg-muted/85" />
            </>
          ) : (
            <span className="text-muted-foreground">Recipe metadata is temporarily unavailable.</span>
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
                  className="line-clamp-1 break-words text-sm text-foreground/85"
                  title={ingredient}
                >
                  • {ingredient}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Ingredient preview is not available for this recipe yet.
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
            Preview is temporarily unavailable. Open the recipe for full details.
          </p>
        )}

        <div className="relative z-20 flex flex-wrap items-center gap-2 pt-1">
          {recipe ? (
            <RecipeBagToggleButton
              recipe={{
                id: recipe.id,
                title: recipe.title,
                servings: recipe.servings,
                total_time: recipe.total_time,
              }}
              size="sm"
            />
          ) : null}
          <div className="inline-flex items-center gap-1.5 text-sm font-medium text-primary">
            {canOpen ? "Open recipe" : "Recipe unavailable"}
            <ArrowRight className="size-4" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

type BrowseResultsGridProps = {
  queryFromUrl: string;
  results: BrowseSearchResult[];
  relatedResultCount: number;
  searchError: string | null;
  isLoadingRelated: boolean;
  isRefiningResults: boolean;
  showLoadRelated: boolean;
  showInitialPrompt: boolean;
  showLoadingGrid: boolean;
  showNoResults: boolean;
  showLoadMore: boolean;
  isLoadingMore: boolean;
  recipeById: Record<string, RecipeRecord>;
  recipeLoadingById: Record<string, boolean>;
  onLoadRelated: () => void;
  onLoadMore: () => void;
  onRetrySearch: () => void;
  onCardOpen: (recipeId: string) => void;
};

export function BrowseResultsGrid({
  queryFromUrl,
  results,
  relatedResultCount,
  searchError,
  isLoadingRelated,
  isRefiningResults,
  showLoadRelated,
  showInitialPrompt,
  showLoadingGrid,
  showNoResults,
  showLoadMore,
  isLoadingMore,
  recipeById,
  recipeLoadingById,
  onLoadRelated,
  onLoadMore,
  onRetrySearch,
  onCardOpen,
}: BrowseResultsGridProps) {
  const isQueryMode = Boolean(queryFromUrl);

  return (
    <section className="space-y-6 ff-animate-enter-delayed">
      <h2 className="font-display text-[clamp(1.8rem,3vw,2.4rem)] tracking-tight">
        {queryFromUrl ? `Results for "${queryFromUrl}"` : "Browse Recipes"}
      </h2>
      {isQueryMode && isRefiningResults ? (
        <p className="text-sm text-muted-foreground">Refining results...</p>
      ) : null}

      {searchError ? (
        <Card className="border-destructive/35 bg-destructive/5 shadow-none">
          <CardHeader>
            <CardTitle>Search Error</CardTitle>
            <CardDescription>{searchError}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" variant="outline" size="sm" onClick={onRetrySearch}>
              Try search again
            </Button>
          </CardContent>
        </Card>
      ) : null}

      {showInitialPrompt ? (
        <Card className="shadow-none">
          <CardHeader>
            <CardTitle>Start with a query</CardTitle>
            <CardDescription>
              Try a dish, cuisine, ingredient, or meal type.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {showLoadingGrid ? (
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(18rem,1fr))]">
          <ResultCardLoading />
          <ResultCardLoading />
          <ResultCardLoading />
          <ResultCardLoading />
          <ResultCardLoading />
          <ResultCardLoading />
        </div>
      ) : null}

      {showNoResults ? (
        <Card className="shadow-none">
          <CardHeader>
            <CardTitle>No recipes found</CardTitle>
            <CardDescription>
              {isQueryMode
                ? `No recipes matched "${queryFromUrl}". Try a broader phrase or fewer keywords.`
                : "No recipes are available yet. Add your first recipe to get started."}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {results.length ? (
        <>
          <div className="grid gap-4 [grid-template-columns:repeat(auto-fit,minmax(18rem,1fr))]">
            {results.map((result) => {
              const recipeId = result.id ?? "";
              const recipe = recipeId ? recipeById[recipeId] : undefined;
              const isDetailsLoading = recipeId
                ? Boolean(recipeLoadingById[recipeId])
                : false;

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

          {showLoadMore ? (
            <div className="flex justify-center pt-2">
              <Button
                type="button"
                variant="outline"
                size="lg"
                onClick={onLoadMore}
                disabled={isLoadingMore}
              >
                {isLoadingMore ? "Loading more..." : "Load more recipes"}
              </Button>
            </div>
          ) : null}
        </>
      ) : null}

      {isQueryMode && (isLoadingRelated || showLoadRelated) ? (
        <Card className="border-border/70 bg-muted/20 shadow-none">
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <CardTitle className="text-lg">Related Recipes</CardTitle>
              <CardDescription>
                {isLoadingRelated
                  ? "Finding related recipes in the background..."
                  : `${relatedResultCount} related recipes are ready to add.`}
              </CardDescription>
            </div>
            {showLoadRelated ? (
              <Button type="button" variant="outline" onClick={onLoadRelated}>
                Load related recipes ({relatedResultCount})
              </Button>
            ) : null}
          </CardHeader>
        </Card>
      ) : null}
    </section>
  );
}
