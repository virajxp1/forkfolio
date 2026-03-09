import Link from "next/link";
import { ArrowLeft, Clock3, Users2 } from "lucide-react";
import { notFound } from "next/navigation";

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

async function loadRecipes(recipeIds: string[]): Promise<LoadedRecipe[]> {
  const settled = await Promise.allSettled(recipeIds.map((recipeId) => getRecipe(recipeId)));
  return settled.map((result, index) => {
    const recipeId = recipeIds[index];
    if (result.status === "fulfilled") {
      return {
        id: recipeId,
        recipe: result.value.recipe,
      };
    }

    return {
      id: recipeId,
      recipe: null,
    };
  });
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

  return (
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <Button asChild variant="ghost" className="mb-4">
          <Link href="/books">
            <ArrowLeft className="size-4" />
            Back to Recipe Books
          </Link>
        </Button>

        {loadError || !recipeBook ? (
          <Card className="border-destructive/35 bg-destructive/5">
            <CardHeader>
              <CardTitle>Unable to load recipe book</CardTitle>
              <CardDescription>{loadError ?? "Something went wrong."}</CardDescription>
            </CardHeader>
          </Card>
        ) : (
          <>
            <Card className="mb-5">
              <CardHeader className="space-y-4">
                <Badge variant="secondary" className="w-fit rounded-full px-3 py-0.5 text-xs">
                  Recipe Book
                </Badge>
                <CardTitle className="font-display text-5xl leading-tight tracking-tight text-primary">
                  {recipeBook.name}
                </CardTitle>
                <CardDescription>
                  {recipeBook.description?.trim() || "No description yet."}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
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

            {missingRecipesCount > 0 ? (
              <Card className="mb-5 border-border/80 bg-background/80">
                <CardHeader>
                  <CardTitle className="text-base">Some recipes could not be loaded</CardTitle>
                  <CardDescription>
                    {missingRecipesCount} recipe{missingRecipesCount === 1 ? "" : "s"} in this
                    book are temporarily unavailable.
                  </CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {!availableRecipes.length ? (
              <Card>
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
            ) : (
              <section className="space-y-5">
                <h2 className="font-display text-3xl tracking-tight">Recipes</h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {availableRecipes.map(({ id, recipe }) => (
                    <Card key={id} className="border-border/80">
                      <CardHeader className="space-y-3">
                        <CardTitle className="font-display text-3xl leading-tight">
                          {recipe.title || "Untitled recipe"}
                        </CardTitle>
                        <div className="flex flex-wrap gap-2 text-sm">
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
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <p className="line-clamp-3 text-sm text-muted-foreground">
                          {recipe.ingredients.slice(0, 3).join(" • ") ||
                            "No ingredient preview available."}
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
      </main>
    </div>
  );
}
