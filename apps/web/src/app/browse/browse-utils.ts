export function normalizeParam(rawParam: string | null): string {
  return (rawParam ?? "").trim();
}

export function buildBrowseHref(query: string, recipeId?: string): string {
  const params = new URLSearchParams();
  if (query) {
    params.set("q", query);
  }
  if (recipeId) {
    params.set("recipe", recipeId);
  }

  const serialized = params.toString();
  return serialized ? `/browse?${serialized}` : "/browse";
}
