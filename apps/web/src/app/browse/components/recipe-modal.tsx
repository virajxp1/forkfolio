import { ExternalLink, X } from "lucide-react";
import Link from "next/link";

import { RecipeBagToggleButton } from "@/components/recipe-bag-toggle-button";
import { RecipeContentColumns } from "@/components/recipe-content-columns";
import { RecipeMetadataBadges } from "@/components/recipe-metadata-badges";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import type { RecipeRecord } from "@/lib/forkfolio-types";

type RecipeModalProps = {
  recipeId: string;
  recipe: RecipeRecord | null;
  isLoading: boolean;
  error: string | null;
  onRetry?: () => void;
  onClose: () => void;
};

export function RecipeModal({
  recipeId,
  recipe,
  isLoading,
  error,
  onRetry,
  onClose,
}: RecipeModalProps) {
  const title = recipe?.title || "Recipe";

  return (
    <Dialog
      open
      onOpenChange={(isOpen) => {
        if (!isOpen) {
          onClose();
        }
      }}
    >
      <DialogContent
        showCloseButton={false}
        aria-describedby={undefined}
        className="w-full max-w-5xl overflow-hidden rounded-2xl border-border/80 bg-background/95 p-0 shadow-2xl sm:max-w-5xl"
      >
        <DialogTitle className="sr-only">{title}</DialogTitle>

        <div className="flex items-start justify-between gap-4 border-b border-border/70 bg-card/45 px-6 py-5">
          <div className="min-w-0 space-y-2">
            {recipe ? (
              <h3
                className="break-words font-display text-4xl leading-tight tracking-tight text-primary sm:text-5xl"
                title={title}
              >
                {title}
              </h3>
            ) : isLoading ? (
              <Skeleton className="h-12 w-72 bg-muted/85" />
            ) : (
              <h3 className="font-display text-4xl leading-tight tracking-tight text-primary sm:text-5xl">
                Recipe
              </h3>
            )}

            {recipe ? (
              <RecipeMetadataBadges servings={recipe.servings} totalTime={recipe.total_time} />
            ) : null}
          </div>

          <div className="flex shrink-0 items-center gap-2">
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

            {recipeId ? (
              <Button asChild variant="outline" size="sm">
                <Link href={`/recipes/${recipeId}`}>
                  Open Full Page
                  <ExternalLink className="size-4" />
                </Link>
              </Button>
            ) : null}

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
            <Card className="border-destructive/35 bg-destructive/5 shadow-none">
              <CardHeader>
                <CardTitle>Unable to load recipe</CardTitle>
                <CardDescription>{error}</CardDescription>
              </CardHeader>
              {onRetry ? (
                <CardContent>
                  <Button type="button" variant="outline" size="sm" onClick={onRetry}>
                    Try loading again
                  </Button>
                </CardContent>
              ) : null}
            </Card>
          ) : null}

          {!error && isLoading && !recipe ? (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-[1fr_1.3fr]">
              <Card className="shadow-none">
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

              <Card className="shadow-none">
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
            <RecipeContentColumns
              ingredients={recipe.ingredients}
              instructions={recipe.instructions}
            />
          ) : null}
        </div>
      </DialogContent>
    </Dialog>
  );
}
