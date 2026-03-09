import Link from "next/link";
import { BookOpenText, Plus, Search, TableOfContents } from "lucide-react";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto flex w-full max-w-6xl items-center px-4 py-10 sm:px-6 sm:py-12">
        <section className="w-full rounded-[2rem] border border-border/70 bg-card/35 px-6 py-10 text-center sm:px-10 sm:py-12">
          <div className="mx-auto max-w-4xl">
            <h1 className="font-display text-5xl leading-tight tracking-tight text-foreground sm:text-6xl">
              Every recipe,
              <span className="mt-2 block text-primary">beautifully kept.</span>
            </h1>

            <p className="mx-auto mt-6 max-w-4xl text-lg leading-snug text-muted-foreground sm:text-xl">
              Import recipes from the web or create your own. Organize them into
              curated recipe books. Search anything, find it instantly.
            </p>

            <div className="mx-auto mt-8 grid max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <Button
                asChild
                size="lg"
                variant="secondary"
                className="h-14 rounded-full px-8 text-lg font-semibold"
              >
                <Link href="/recipes/new">
                  <Plus className="size-5" />
                  Add Your First Recipe
                </Link>
              </Button>

              <Button
                asChild
                size="lg"
                variant="secondary"
                className="h-14 rounded-full px-8 text-lg font-semibold"
              >
                <Link href="/books">
                  <BookOpenText className="size-5" />
                  Recipe Books
                </Link>
              </Button>

              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-14 rounded-full border-2 border-primary px-8 text-lg font-semibold text-primary hover:bg-primary/10"
              >
                <Link href="/browse">
                  <Search className="size-5" />
                  Browse Recipes
                </Link>
              </Button>

              <Button
                asChild
                size="lg"
                variant="outline"
                className="h-14 rounded-full border-2 border-border px-8 text-lg font-semibold"
              >
                <Link href="/browse-all">
                  <TableOfContents className="size-5" />
                  Browse All
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
