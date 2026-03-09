"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

import { BrowseResultsGrid } from "./components/browse-results-grid";
import { BrowseSearchForm } from "./components/browse-search-form";
import { RecipeModal } from "./components/recipe-modal";
import { useBrowseData } from "./use-browse-data";

export default function BrowsePage() {
  const {
    queryFromUrl,
    queryInput,
    results,
    searchError,
    isSearching,
    recipeById,
    recipeLoadingById,
    recipeIdFromUrl,
    selectedRecipe,
    selectedRecipeLoading,
    selectedRecipeError,
    hasModal,
    showInitialPrompt,
    showLoadingGrid,
    showNoResults,
    handleSearchSubmit,
    handleQueryInputChange,
    openRecipeModal,
    closeRecipeModal,
  } = useBrowseData();

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
                  Browse Recipes
                </Badge>
                <h1 className="font-display text-5xl tracking-tight sm:text-6xl">
                  Find anything instantly
                </h1>
                <p className="text-lg text-muted-foreground">
                  Search your collection and open any result to view full recipe details.
                </p>
              </div>

              <BrowseSearchForm
                queryInput={queryInput}
                isSearching={isSearching}
                onQueryInputChange={handleQueryInputChange}
                onSearchSubmit={handleSearchSubmit}
              />
            </div>
          </section>

          <BrowseResultsGrid
            queryFromUrl={queryFromUrl}
            results={results}
            searchError={searchError}
            showInitialPrompt={showInitialPrompt}
            showLoadingGrid={showLoadingGrid}
            showNoResults={showNoResults}
            recipeById={recipeById}
            recipeLoadingById={recipeLoadingById}
            onCardOpen={openRecipeModal}
          />
        </main>
      </div>

      {hasModal ? (
        <RecipeModal
          recipeId={recipeIdFromUrl}
          recipe={selectedRecipe}
          isLoading={selectedRecipeLoading && !selectedRecipe}
          error={selectedRecipeError}
          onClose={closeRecipeModal}
        />
      ) : null}
    </div>
  );
}
