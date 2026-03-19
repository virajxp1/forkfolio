import { notFound } from "next/navigation";

import { DeleteRecipeButton } from "@/components/delete-recipe-button";
import { ForkfolioHeader } from "@/components/forkfolio-header";
import { PageBackLink, PageHero, PageMain, PageShell } from "@/components/page-shell";
import { RecipeBagToggleButton } from "@/components/recipe-bag-toggle-button";
import { RecipeBookMembership } from "@/components/recipe-book-membership";
import { RecipeContentColumns } from "@/components/recipe-content-columns";
import { RecipeMetadataBadges } from "@/components/recipe-metadata-badges";
import { TrackRecipeHistory } from "@/components/track-recipe-history";
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
      <PageShell>
        <ForkfolioHeader />
        <PageMain className="max-w-3xl space-y-5 ff-animate-enter">
          <PageBackLink href="/browse" label="Back to Search" />

          <Card className="border-destructive/35 bg-destructive/5 shadow-none">
            <CardHeader>
              <CardTitle>Unable to load recipe</CardTitle>
              <CardDescription>
                {apiErrorMessage ?? "Something went wrong."}
              </CardDescription>
            </CardHeader>
          </Card>
        </PageMain>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <TrackRecipeHistory
        recipeId={recipe.id}
        recipeTitle={recipe.title || "Untitled recipe"}
      />
      <ForkfolioHeader />
      <PageMain className="space-y-6 ff-animate-enter">
        <PageBackLink href="/browse" label="Back to Search" />

        <PageHero
          badge="Recipe"
          title={recipe.title || "Untitled recipe"}
          contentClassName="max-w-5xl"
        >
          <RecipeMetadataBadges
            servings={recipe.servings}
            totalTime={recipe.total_time}
            sourceUrl={recipe.source_url}
            showSourceUrl
          />

          <Card className="border-border/80 bg-background/82 shadow-none">
            <CardContent className="space-y-5 pt-6 text-sm text-muted-foreground">
              <div className="flex flex-wrap gap-x-5 gap-y-1 break-words">
                {recipe.created_at ? <span>Created: {recipe.created_at}</span> : null}
                {recipe.updated_at ? <span>Updated: {recipe.updated_at}</span> : null}
              </div>
              <div>
                <RecipeBagToggleButton
                  recipe={{
                    id: recipe.id,
                    title: recipe.title,
                    servings: recipe.servings,
                    total_time: recipe.total_time,
                  }}
                />
              </div>
              <Separator />
              <div>
                <DeleteRecipeButton
                  recipeId={recipe.id}
                  recipeTitle={recipe.title || "Untitled recipe"}
                />
              </div>
            </CardContent>
          </Card>
        </PageHero>

        <section>
          <RecipeBookMembership recipeId={recipe.id} />
        </section>

        <RecipeContentColumns
          ingredients={recipe.ingredients}
          instructions={recipe.instructions}
        />
      </PageMain>
    </PageShell>
  );
}
