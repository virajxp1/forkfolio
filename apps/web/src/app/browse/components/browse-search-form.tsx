import { Search } from "lucide-react";
import { FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

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
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSearchSubmit();
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 sm:flex-row">
      <div className="relative flex-1">
        <Search className="pointer-events-none absolute top-1/2 left-3.5 size-5 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="search"
          name="q"
          value={queryInput}
          onChange={(event) => {
            onQueryInputChange(event.target.value);
          }}
          placeholder="Search recipes... e.g. 'creamy pasta' or 'quick breakfast'"
          className="h-14 rounded-2xl border-border/90 bg-background pl-11 text-base"
        />
      </div>
      <Button
        type="submit"
        size="lg"
        className="h-14 rounded-2xl px-8 text-lg"
        disabled={isSearching}
      >
        Search
      </Button>
    </form>
  );
}
