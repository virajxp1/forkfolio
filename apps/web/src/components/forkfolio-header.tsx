"use client";

import Link from "next/link";
import { BookOpenText, Plus, Search, ShoppingBag, UtensilsCrossed } from "lucide-react";

import { useGroceryBag } from "@/components/grocery-bag-provider";
import { Button } from "@/components/ui/button";

export function ForkfolioHeader() {
  const { itemCount } = useGroceryBag();

  return (
    <header className="sticky top-0 z-20 border-b border-border/70 bg-background/95 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-foreground transition-colors hover:text-primary"
        >
          <UtensilsCrossed className="size-6 text-primary" />
          <span className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">
            ForkFolio
          </span>
        </Link>

        <nav className="flex items-center gap-2">
          <Button asChild variant="secondary" size="sm">
            <Link href="/browse">
              <Search className="size-4" />
              Browse
            </Link>
          </Button>
          <Button asChild variant="secondary" size="sm">
            <Link href="/books">
              <BookOpenText className="size-4" />
              Books
            </Link>
          </Button>
          <Button asChild variant="secondary" size="sm">
            <Link href="/recipes/new">
              <Plus className="size-4" />
              Add Recipe
            </Link>
          </Button>
          <Button asChild variant="secondary" size="sm">
            <Link href="/bag">
              <ShoppingBag className="size-4" />
              Bag
              {itemCount ? (
                <span className="inline-flex min-w-6 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground">
                  {itemCount}
                </span>
              ) : null}
            </Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}
