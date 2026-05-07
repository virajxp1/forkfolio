"use client";

import Link from "next/link";
import {
  BookOpenText,
  FlaskConical,
  Plus,
  Search,
  ShoppingBag,
  UtensilsCrossed,
} from "lucide-react";
import { usePathname } from "next/navigation";

import { AuthProfileButton } from "@/components/auth-profile-button";
import { useGroceryBag } from "@/components/grocery-bag-provider";
import { Button, buttonVariants } from "@/components/ui/button";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  {
    href: "/browse",
    label: "Browse",
    icon: Search,
  },
  {
    href: "/books",
    label: "Books",
    icon: BookOpenText,
  },
  {
    href: "/experiment",
    label: "Experiment",
    icon: FlaskConical,
  },
  {
    href: "/recipes/new",
    label: "Add Recipe",
    icon: Plus,
  },
] as const;

function isRouteActive(pathname: string, href: string): boolean {
  if (pathname === href) {
    return true;
  }
  if (href === "/") {
    return pathname === "/";
  }
  return pathname.startsWith(`${href}/`);
}

export function ForkfolioHeader() {
  const pathname = usePathname() ?? "/";
  const { itemCount, items } = useGroceryBag();
  const previewItems = items.slice(0, 3);
  const bagActive = isRouteActive(pathname, "/bag");

  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/90 backdrop-blur-xl">
      <div className="mx-auto w-full max-w-6xl px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2.5 text-foreground transition-colors hover:text-primary"
          >
            <span className="inline-flex size-9 items-center justify-center rounded-full bg-primary/15 text-primary">
              <UtensilsCrossed className="size-5" />
            </span>
            <span className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
              ForkFolio
            </span>
          </Link>

          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
            <nav className="grid w-full grid-cols-2 gap-2 sm:w-auto sm:auto-cols-max sm:grid-flow-col sm:grid-cols-none sm:gap-1.5">
              {NAV_ITEMS.map((item) => {
                const active = isRouteActive(pathname, item.href);

                return (
                  <Button
                    key={item.href}
                    asChild
                    variant={active ? "default" : "secondary"}
                    size="sm"
                    className="h-9 rounded-full px-3.5"
                  >
                    <Link href={item.href} aria-current={active ? "page" : undefined}>
                      <item.icon className="size-4" />
                      {item.label}
                    </Link>
                  </Button>
                );
              })}

              <HoverCard openDelay={150}>
                <HoverCardTrigger asChild>
                  <Link
                    href="/bag"
                    aria-current={bagActive ? "page" : undefined}
                    className={cn(
                      buttonVariants({ variant: bagActive ? "default" : "secondary", size: "sm" }),
                      "h-9 rounded-full px-3.5",
                    )}
                  >
                    <ShoppingBag className="size-4" />
                    Bag
                    {itemCount ? (
                      <span
                        className={cn(
                          "inline-flex min-w-6 items-center justify-center rounded-full px-1.5 text-xs font-semibold",
                          bagActive ? "bg-background text-foreground" : "bg-primary text-primary-foreground",
                        )}
                      >
                        {itemCount}
                      </span>
                    ) : null}
                  </Link>
                </HoverCardTrigger>
                <HoverCardContent
                  align="end"
                  className="w-[min(20rem,calc(100vw-2rem))] space-y-3 rounded-xl border-border/80 bg-background/95"
                >
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
                        <div
                          key={item.id}
                          className="rounded-lg border border-border/70 bg-card/60 px-2.5 py-2"
                        >
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

            <AuthProfileButton />
          </div>
        </div>
      </div>
    </header>
  );
}
