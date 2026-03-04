"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState, useTransition } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

type BrowseSearchFormProps = {
  initialQuery: string;
};

export function BrowseSearchForm({ initialQuery }: BrowseSearchFormProps) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);
  const [isClearing, startTransition] = useTransition();
  const [isSubmitting, startSubmitTransition] = useTransition();

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedQuery = query.trim();
    startSubmitTransition(() => {
      if (!normalizedQuery) {
        router.push("/browse", { scroll: false });
        return;
      }
      const params = new URLSearchParams({ q: normalizedQuery });
      router.push(`/browse?${params.toString()}`, { scroll: false });
    });
  }

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            name="q"
            value={query}
            onChange={(event) => {
              const nextQuery = event.target.value;
              setQuery(nextQuery);
              if (nextQuery.trim() === "") {
                startTransition(() => {
                  router.replace("/browse", { scroll: false });
                });
              }
            }}
            placeholder="Search recipes... e.g. 'creamy pasta' or 'quick breakfast'"
            className="h-14 rounded-2xl border-border/90 bg-background pl-11 text-base"
          />
        </div>
        <Button
          type="submit"
          size="lg"
          className="h-14 rounded-2xl px-8 text-lg"
          disabled={isClearing || isSubmitting}
        >
          Search
        </Button>
      </form>

      {isSubmitting ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <Skeleton className="h-36 rounded-xl" />
          <Skeleton className="h-36 rounded-xl" />
          <Skeleton className="h-36 rounded-xl" />
        </div>
      ) : null}
    </div>
  );
}
