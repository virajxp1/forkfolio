import { Search } from "lucide-react";
import { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

type BrowseSearchFormProps = {
  queryInput: string;
  isSearching: boolean;
  onQueryInputChange: (value: string) => void;
  onSearchSubmit: () => void;
};

export function BrowseSearchForm({
  queryInput,
  isSearching,
  onQueryInputChange,
  onSearchSubmit,
}: BrowseSearchFormProps) {
  const normalizedQuery = queryInput.trim();
  const isShortQuery = normalizedQuery.length > 0 && normalizedQuery.length < 2;

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearchSubmit();
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <Label htmlFor="browse-search-input" className="sr-only">
        Search recipes
      </Label>

      <div className="flex flex-col gap-3 sm:flex-row">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-muted-foreground/80" />
          <Input
            id="browse-search-input"
            type="search"
            name="q"
            value={queryInput}
            onChange={(event) => {
              onQueryInputChange(event.target.value);
            }}
            placeholder="Search by dish, ingredient, cuisine, or dietary goal"
            autoComplete="off"
            aria-describedby="browse-search-hint"
            aria-invalid={isShortQuery}
            className="h-14 rounded-2xl border-border/85 bg-background/85 pl-11 text-base"
          />
        </div>

        <Button
          type="submit"
          size="lg"
          className="h-14 rounded-2xl px-8 text-base sm:text-lg"
          disabled={isSearching}
        >
          {isSearching ? "Searching..." : "Search"}
        </Button>
      </div>

      <p
        id="browse-search-hint"
        className={cn(
          "text-sm",
          isShortQuery ? "text-destructive" : "text-muted-foreground",
        )}
      >
        {isShortQuery
          ? "Use at least 2 characters for best matches."
          : "Search titles first, then add related semantic matches when available."}
      </p>
    </form>
  );
}
