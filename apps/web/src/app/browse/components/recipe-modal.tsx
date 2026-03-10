import { Clock3, ExternalLink, Users2, X } from "lucide-react";
import Link from "next/link";

import { RecipeBagToggleButton } from "@/components/recipe-bag-toggle-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { RecipeRecord } from "@/lib/forkfolio-types";

type RecipeModalProps = {
  recipeId: string;
  recipe: RecipeRecord | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
};

export function RecipeModal({
  recipeId,
  recipe,
  isLoading,
  error,
  onClose,
}: RecipeModalProps) {
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
                      <li key={`${instruction}-${index}`} className="flex items-start gap-3">
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
