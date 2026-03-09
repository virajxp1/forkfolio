"use client";

import { ArrowLeft, ListFilter, RefreshCw } from "lucide-react";
import Link from "next/link";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

import { BrowseResultsGrid } from "../browse/components/browse-results-grid";
import { RecipeModal } from "../browse/components/recipe-modal";
import { useBrowseAllData } from "./use-browse-all-data";

export default function BrowseAllPage() {
  const {
    results,
    loadError,
    isLoading,
    recipeById,
    recipeLoadingById,
    selectedRecipeId,
    selectedRecipe,
    selectedRecipeLoading,
    selectedRecipeError,
    hasModal,
    showNoResults,
    openRecipeModal,
    closeRecipeModal,
    reloadAllRecipes,
  } = useBrowseAllData();

  return (
    <div className="min-h-screen">
      <div className={hasModal ? "pointer-events-none select-none blur-[3px]" : ""}>
        <ForkfolioHeader />

        <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
          <Button asChild variant="ghost" className="mb-4">
            <Link href="/">
              <ArrowLeft className="size-4" />
              Back to Home
            </Link>
          </Button>

          <section className="rounded-[2rem] border border-border/70 bg-card/35 px-6 py-10 sm:px-10">
            <div className="mx-auto max-w-4xl space-y-6">
              <div className="space-y-2">
                <Badge variant="secondary" className="rounded-full px-3 py-0.5 text-xs">
                  Browse All
                </Badge>
                <h1 className="font-display text-5xl tracking-tight sm:text-6xl">
                  Every recipe in one view
                </h1>
                <p className="text-lg text-muted-foreground">
                  Recipes are listed in alphabetical order. Open a card for full
                  `/all` recipe data.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    void reloadAllRecipes();
                  }}
                  disabled={isLoading}
                >
                  <RefreshCw className={`size-4 ${isLoading ? "animate-spin" : ""}`} />
                  Refresh
                </Button>
                <Badge variant="outline" className="gap-1.5">
                  <ListFilter className="size-3.5" />
                  A to Z
                </Badge>
              </div>
            </div>
          </section>

          {loadError ? (
            <Card className="mt-10 border-destructive/35 bg-destructive/5">
              <CardHeader>
                <CardTitle>Unable to load recipes</CardTitle>
                <CardDescription>{loadError}</CardDescription>
              </CardHeader>
            </Card>
          ) : null}

          <BrowseResultsGrid
            heading="All Recipes"
            queryFromUrl=""
            results={results}
            searchError={null}
            showInitialPrompt={false}
            showLoadingGrid={isLoading}
            showNoResults={showNoResults}
            recipeById={recipeById}
            recipeLoadingById={recipeLoadingById}
            onCardOpen={openRecipeModal}
          />
        </main>
      </div>

      {hasModal && selectedRecipeId ? (
        <RecipeModal
          recipeId={selectedRecipeId}
          recipe={selectedRecipe}
          isLoading={selectedRecipeLoading && !selectedRecipe}
          error={selectedRecipeError}
          onClose={closeRecipeModal}
        />
      ) : null}
    </div>
  );
}
