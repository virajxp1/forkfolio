"use client";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { PageBackLink, PageHero, PageMain, PageShell } from "@/components/page-shell";

import { BrowseResultsGrid } from "./components/browse-results-grid";
import { BrowseSearchForm } from "./components/browse-search-form";
import { RecipeModal } from "./components/recipe-modal";
import { useBrowseData } from "./use-browse-data";

export default function BrowsePage() {
  const {
    queryFromUrl,
    queryInput,
    results,
    relatedResultCount,
    searchError,
    isSearching,
    isLoadingRelated,
    showLoadRelated,
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
    showLoadMore,
    isLoadingMore,
    handleSearchSubmit,
    handleQueryInputChange,
    handleLoadRelated,
    handleLoadMore,
    openRecipeModal,
    closeRecipeModal,
  } = useBrowseData();

  return (
    <PageShell>
      <div className={hasModal ? "pointer-events-none select-none blur-[3px]" : ""}>
        <ForkfolioHeader />

        <PageMain className="space-y-8 ff-animate-enter">
          <PageBackLink href="/" label="Back to Home" />

          <PageHero
            badge="Browse Recipes"
            title="Find anything instantly"
            description="Browse your latest recipes or search by dish, ingredient, or cuisine."
            contentClassName="max-w-4xl"
          >
            <BrowseSearchForm
              queryInput={queryInput}
              isSearching={isSearching}
              onQueryInputChange={handleQueryInputChange}
              onSearchSubmit={handleSearchSubmit}
            />
          </PageHero>

          <BrowseResultsGrid
            queryFromUrl={queryFromUrl}
            results={results}
            relatedResultCount={relatedResultCount}
            searchError={searchError}
            isLoadingRelated={isLoadingRelated}
            showLoadRelated={showLoadRelated}
            showInitialPrompt={showInitialPrompt}
            showLoadingGrid={showLoadingGrid}
            showNoResults={showNoResults}
            showLoadMore={showLoadMore}
            isLoadingMore={isLoadingMore}
            onLoadRelated={handleLoadRelated}
            recipeById={recipeById}
            recipeLoadingById={recipeLoadingById}
            onLoadMore={handleLoadMore}
            onCardOpen={openRecipeModal}
          />
        </PageMain>
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
    </PageShell>
  );
}
