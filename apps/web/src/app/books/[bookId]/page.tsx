import Link from "next/link";
import { notFound } from "next/navigation";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { PageBackLink, PageHero, PageMain, PageShell } from "@/components/page-shell";
import { RecipeMetadataBadges } from "@/components/recipe-metadata-badges";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  getRecipe,
  getRecipeBook,
  isForkfolioApiError,
  type RecipeRecord,
} from "@/lib/forkfolio-api";

type RecipeBookDetailPageProps = {
  params: Promise<{ bookId: string }>;
};

type LoadedRecipe = {
  id: string;
  recipe: RecipeRecord | null;
};

const RECIPE_FETCH_BATCH_SIZE = 8;

async function loadRecipes(recipeIds: string[]): Promise<LoadedRecipe[]> {
  const loadedRecipes: LoadedRecipe[] = [];

  for (let index = 0; index < recipeIds.length; index += RECIPE_FETCH_BATCH_SIZE) {
    const batchIds = recipeIds.slice(index, index + RECIPE_FETCH_BATCH_SIZE);
    const settled = await Promise.allSettled(
      batchIds.map((recipeId) => getRecipe(recipeId)),
    );

    for (let settledIndex = 0; settledIndex < settled.length; settledIndex += 1) {
      const result = settled[settledIndex];
      const recipeId = batchIds[settledIndex];

      if (result.status === "fulfilled") {
        loadedRecipes.push({
          id: recipeId,
          recipe: result.value.recipe,
        });
      } else {
        loadedRecipes.push({
          id: recipeId,
          recipe: null,
        });
      }
    }
  }

  return loadedRecipes;
}

export default async function RecipeBookDetailPage({ params }: RecipeBookDetailPageProps) {
  const { bookId } = await params;

  let loadError: string | null = null;
  let recipeBook:
    | {
        id: string;
        name: string;
        normalized_name: string;
        description: string | null;
        created_at: string | null;
        updated_at: string | null;
        recipe_count: number;
        recipe_ids?: string[];
      }
    | null = null;

  try {
    const response = await getRecipeBook(bookId);
    recipeBook = response.recipe_book;
  } catch (error) {
    if (isForkfolioApiError(error) && error.status === 404) {
      notFound();
    }
    loadError = isForkfolioApiError(error)
      ? error.detail ?? "Failed to load recipe book."
      : "Failed to load recipe book.";
  }

  const recipeIds = recipeBook?.recipe_ids ?? [];
  const loadedRecipes = recipeBook ? await loadRecipes(recipeIds) : [];
  const availableRecipes = loadedRecipes.filter(
    (loadedRecipe): loadedRecipe is { id: string; recipe: RecipeRecord } =>
      loadedRecipe.recipe !== null,
  );
  const missingRecipesCount = loadedRecipes.length - availableRecipes.length;
  const allRecipesUnavailable =
    recipeIds.length > 0 && availableRecipes.length === 0 && missingRecipesCount > 0;

  return (
    <PageShell>
      <ForkfolioHeader />

      <PageMain className="space-y-6 ff-animate-enter">
        <PageBackLink href="/books" label="Back to Recipe Books" />

        {loadError || !recipeBook ? (
          <Card className="border-destructive/35 bg-destructive/5 shadow-none">
            <CardHeader>
              <CardTitle>Unable to load recipe book</CardTitle>
              <CardDescription>{loadError ?? "Something went wrong."}</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <>
            <PageHero
              badge="Recipe Book"
              title={recipeBook.name}
              description={recipeBook.description?.trim() || "No description yet."}
              contentClassName="max-w-5xl"
            >
              <Card className="border-border/80 bg-background/82 shadow-none">
                <CardContent className="space-y-4 pt-6">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline">
                    {recipeBook.recipe_count} recipe{recipeBook.recipe_count === 1 ? "" : "s"}
                  </Badge>
                  {recipeBook.created_at ? <Badge variant="outline">Created: {recipeBook.created_at}</Badge> : null}
                  {recipeBook.updated_at ? <Badge variant="outline">Updated: {recipeBook.updated_at}</Badge> : null}
                </div>

                <Separator />

                <p className="text-sm text-muted-foreground">
                  Book ID: {recipeBook.id}
                </p>
                </CardContent>
              </Card>
            </PageHero>

            {missingRecipesCount > 0 && !allRecipesUnavailable ? (
              <Card className="border-border/80 bg-background/80 shadow-none">
                <CardHeader>
                  <CardTitle className="text-base">Some recipes could not be loaded</CardTitle>
                  <CardDescription>
                    {missingRecipesCount} recipe{missingRecipesCount === 1 ? "" : "s"} in this
                    book are temporarily unavailable.
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {!recipeIds.length ? (
              <Card className="shadow-none">
                <CardHeader>
                  <CardTitle>No recipes in this book yet</CardTitle>
                  <CardDescription>
                    Open any recipe and add it to this book from the Recipe Books panel.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button asChild variant="secondary">
                    <Link href="/browse">Browse Recipes</Link>
                  </Button>
                </CardContent>
              </Card>
            ) : allRecipesUnavailable ? (
              <Card className="shadow-none">
                <CardHeader>
                  <CardTitle>Recipes are currently unavailable</CardTitle>
                  <CardDescription>
                    This book has {recipeIds.length} recipe
                    {recipeIds.length === 1 ? "" : "s"}, but none could be loaded right now.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Button asChild variant="secondary">
                    <Link href="/browse">Browse Recipes</Link>
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <section className="space-y-5">
                <h2 className="font-display text-3xl tracking-tight">Recipes</h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {availableRecipes.map(({ id, recipe }) => (
                    <Card key={id} className="border-border/80 bg-background/80 shadow-none">
                      <CardHeader className="space-y-3">
                        <CardTitle
                          className="line-clamp-2 break-words font-display text-3xl leading-tight"
                          title={recipe.title || "Untitled recipe"}
                        >
                          {recipe.title || "Untitled recipe"}
                        </CardTitle>
                        <RecipeMetadataBadges
                          servings={recipe.servings}
                          totalTime={recipe.total_time}
                          isPublic={recipe.is_public}
                        />
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <p className="line-clamp-3 break-words text-sm text-muted-foreground">
                          {recipe.ingredients.slice(0, 3).join(" • ") ||
                            "No ingredient preview is available yet."}
                        </p>
                        <Button asChild variant="outline" size="sm">
                          <Link href={`/recipes/${recipe.id}`}>Open Recipe</Link>
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </PageMain>
    </PageShell>
  );
}
