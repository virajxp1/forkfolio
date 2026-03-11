"use client";

import Link from "next/link";
import { BookOpenText, Plus, Search, ShoppingBag, UtensilsCrossed } from "lucide-react";

import { useGroceryBag } from "@/components/grocery-bag-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { cn } from "@/lib/utils";

export function ForkfolioHeader() {
  const { itemCount, items } = useGroceryBag();
  const previewItems = items.slice(0, 3);

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
          <HoverCard openDelay={150}>
            <HoverCardTrigger asChild>
              <Link
                href="/bag"
                className={cn(buttonVariants({ variant: "secondary", size: "sm" }))}
              >
                <ShoppingBag className="size-4" />
                Bag
                {itemCount ? (
                  <span className="inline-flex min-w-6 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-primary-foreground">
                    {itemCount}
                  </span>
                ) : null}
              </Link>
            </HoverCardTrigger>
            <HoverCardContent align="end" className="w-80 space-y-3">
              <div className="space-y-1">
                <p className="text-sm font-medium">Bag Preview</p>
                <p className="text-xs text-muted-foreground">
                  {itemCount} recipe{itemCount === 1 ? "" : "s"} selected
                </p>
              </div>

              {!itemCount ? (
                <p className="text-sm text-muted-foreground">
                  Add recipes from browse or detail pages to build your grocery list.
                </p>
              ) : (
                <div className="space-y-2">
                  {previewItems.map((item) => (
                    <div key={item.id} className="rounded-md border border-border/70 px-2.5 py-2">
                      <p className="truncate text-sm font-medium">{item.title || "Untitled recipe"}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {item.total_time || item.servings || "No metadata"}
                      </p>
                    </div>
                  ))}
                  {itemCount > previewItems.length ? (
                    <p className="text-xs text-muted-foreground">
                      +{itemCount - previewItems.length} more in bag
                    </p>
                  ) : null}
                </div>
              )}
            </HoverCardContent>
          </HoverCard>
        </nav>
      </div>
    </header>
  );
}
