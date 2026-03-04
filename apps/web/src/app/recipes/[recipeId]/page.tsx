import Link from "next/link";
import { ArrowLeft, Clock3, LinkIcon, Users2 } from "lucide-react";
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
  isForkfolioApiError,
  type RecipeRecord,
} from "@/lib/forkfolio-api";

type RecipePageProps = {
  params: Promise<{ recipeId: string }>;
};

function MetadataBadges({ recipe }: { recipe: RecipeRecord }) {
  return (
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
      {recipe.source_url ? (
        <Badge variant="outline" className="max-w-full gap-1.5 truncate">
          <LinkIcon className="size-3.5" />
          <span className="truncate">{recipe.source_url}</span>
        </Badge>
      ) : null}
    </div>
  );
}

function RecipeBody({ recipe }: { recipe: RecipeRecord }) {
  return (
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
  );
}

export default async function RecipeDetailPage({ params }: RecipePageProps) {
  const { recipeId } = await params;

  let recipe: RecipeRecord | null = null;
  let apiErrorMessage: string | null = null;

  try {
    const response = await getRecipe(recipeId);
    recipe = response.recipe;
  } catch (error) {
    if (isForkfolioApiError(error) && error.status === 404) {
      notFound();
    }
    apiErrorMessage = isForkfolioApiError(error)
      ? error.detail ?? "Failed to fetch recipe."
      : "Failed to fetch recipe.";
  }

  if (!recipe) {
    return (
      <div className="min-h-screen">
        <ForkfolioHeader />
        <main className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
          <Button asChild variant="ghost" className="mb-4">
            <Link href="/browse">
              <ArrowLeft className="size-4" />
              Back to Search
            </Link>
          </Button>

          <Card className="border-destructive/35 bg-destructive/5">
            <CardHeader>
              <CardTitle>Unable to load recipe</CardTitle>
              <CardDescription>
                {apiErrorMessage ?? "Something went wrong."}
              </CardDescription>
            </CardHeader>
          </Card>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <ForkfolioHeader />
      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <Button asChild variant="ghost" className="mb-4">
          <Link href="/browse">
            <ArrowLeft className="size-4" />
            Back to Search
          </Link>
        </Button>

        <Card className="mb-5">
          <CardHeader className="space-y-4">
            <CardTitle className="font-display text-5xl leading-tight tracking-tight text-primary">
              {recipe.title || "Untitled recipe"}
            </CardTitle>
            <MetadataBadges recipe={recipe} />
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <div className="flex flex-wrap gap-x-5 gap-y-1">
              {recipe.created_at ? <span>Created: {recipe.created_at}</span> : null}
              {recipe.updated_at ? <span>Updated: {recipe.updated_at}</span> : null}
            </div>
            <Separator className="mt-5" />
          </CardContent>
        </Card>

        <RecipeBody recipe={recipe} />
      </main>
    </div>
  );
}
