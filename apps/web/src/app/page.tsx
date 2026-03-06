import Link from "next/link";
import { Plus, Search } from "lucide-react";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto flex w-full max-w-6xl items-center px-4 py-14 sm:px-6 sm:py-20">
        <section className="w-full rounded-[2rem] border border-border/70 bg-card/35 px-6 py-12 text-center sm:px-12 sm:py-16">
          <div className="mx-auto max-w-4xl">
            <h1 className="font-display text-5xl leading-tight tracking-tight text-foreground sm:text-7xl">
              Every recipe,
              <span className="mt-2 block text-primary">beautifully kept.</span>
            </h1>

            <p className="mx-auto mt-8 max-w-4xl text-xl leading-snug text-muted-foreground sm:text-2xl">
              Import recipes from the web or create your own. Organize them into
              curated recipe books. Search anything, find it instantly.
            </p>

            <div className="mx-auto mt-12 flex max-w-4xl flex-col gap-4 sm:flex-row sm:justify-center">
              <Button
                asChild
                size="lg"
                variant="secondary"
                className="h-16 rounded-full px-12 text-lg font-semibold sm:flex-1 sm:text-2xl"
              >
                <Link href="/recipes/new">
                  <Plus className="size-6" />
                  Add Your First Recipe
                </Link>
              </Button>

              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-16 rounded-full border-2 border-primary px-12 text-lg font-semibold text-primary hover:bg-primary/10 sm:flex-1 sm:text-2xl"
              >
                <Link href="/browse">
                  <Search className="size-6" />
                  Browse Recipes
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
