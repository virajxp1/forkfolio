import type {
  GetRecipeResponse,
  ListRecipesResponse,
  SearchRecipesResponse,
} from "@/lib/forkfolio-types";

const SEARCH_LIMIT = 12;
export const MIN_QUERY_LENGTH = 2;
export const MIN_TEXT_MATCH_QUERY_LENGTH = 3;

type ErrorPayload = {
  detail?: string;
  error?: string;
};

export class BrowserApiError extends Error {
  status: number;

  detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = "BrowserApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof BrowserApiError) {
    return error.detail ?? error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

async function readErrorPayload(response: Response): Promise<ErrorPayload | null> {
  try {
    return (await response.json()) as ErrorPayload;
  } catch {
    return null;
  }
}

async function browserFetch<T>(pathWithQuery: string): Promise<T> {
  const path = pathWithQuery.startsWith("/") ? pathWithQuery : `/${pathWithQuery}`;
  const response = await fetch(path, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detail = payload?.detail ?? payload?.error ?? null;
    throw new BrowserApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

export async function searchRecipesClient(
  query: string,
  limit = SEARCH_LIMIT,
): Promise<SearchRecipesResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  return browserFetch<SearchRecipesResponse>(`/api/search?${params.toString()}`);
}

export async function searchRecipesByNameClient(
  query: string,
  limit = SEARCH_LIMIT,
): Promise<SearchRecipesResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  return browserFetch<SearchRecipesResponse>(`/api/search/names?${params.toString()}`);
}

export async function listRecipesClient(
  limit = SEARCH_LIMIT,
  cursor?: string,
): Promise<ListRecipesResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor?.trim()) {
    params.set("cursor", cursor.trim());
  }
  return browserFetch<ListRecipesResponse>(`/api/recipes?${params.toString()}`);
}

export async function getRecipeClient(recipeId: string): Promise<GetRecipeResponse> {
  return browserFetch<GetRecipeResponse>(`/api/recipes/${recipeId}`);
}
