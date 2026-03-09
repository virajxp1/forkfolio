import type { GetRecipeResponse, ListRecipesResponse } from "@/lib/forkfolio-types";

const DEFAULT_LIST_LIMIT = 500;

type ErrorPayload = {
  detail?: string;
  error?: string;
  message?: string;
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
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detail = payload?.detail ?? payload?.error ?? payload?.message ?? null;
    throw new BrowserApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

export async function listRecipesClient(
  limit = DEFAULT_LIST_LIMIT,
): Promise<ListRecipesResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return browserFetch<ListRecipesResponse>(`/api/recipes?${params.toString()}`);
}

export async function getRecipeAllClient(recipeId: string): Promise<GetRecipeResponse> {
  return browserFetch<GetRecipeResponse>(`/api/recipes/${encodeURIComponent(recipeId)}/all`);
}
