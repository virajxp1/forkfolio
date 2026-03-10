import "server-only";

import type {
  AddRecipeToBookResponse,
  ApiErrorPayload,
  CreateRecipeBookRequest,
  CreateRecipeBookResponse,
  GetRecipeResponse,
  PreviewRecipeFromUrlRequest,
  PreviewRecipeFromUrlResponse,
  GetRecipeBookResponse,
  GetRecipeBooksForRecipeResponse,
  GetRecipeBookStatsResponse,
  ListRecipeBooksResponse,
  ListRecipesResponse,
  ProcessRecipeRequest,
  ProcessRecipeResponse,
  RecipeRecord,
  RemoveRecipeFromBookResponse,
  SearchRecipesResponse,
} from "@/lib/forkfolio-types";

const DEFAULT_API_BASE_URL = "https://forkfolio-be.onrender.com";
const DEFAULT_API_BASE_PATH = "/api/v1";

function normalizeApiBasePath(rawPath: string): string {
  const normalized = rawPath.trim();
  if (!normalized) {
    return DEFAULT_API_BASE_PATH;
  }

  const prefixed = normalized.startsWith("/") ? normalized : `/${normalized}`;
  return prefixed.endsWith("/") ? prefixed.slice(0, -1) : prefixed;
}

const API_BASE_URL = (
  process.env.FORKFOLIO_API_BASE_URL ?? DEFAULT_API_BASE_URL
).replace(/\/+$/, "");
const API_BASE_PATH = normalizeApiBasePath(
  process.env.FORKFOLIO_API_BASE_PATH ?? DEFAULT_API_BASE_PATH,
);
const API_TOKEN = process.env.FORKFOLIO_API_TOKEN?.trim() ?? "";

export class ForkfolioApiError extends Error {
  status: number;

  detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = "ForkfolioApiError";
    this.status = status;
    this.detail = detail;
  }
}

export function isForkfolioApiError(error: unknown): error is ForkfolioApiError {
  return error instanceof ForkfolioApiError;
}

function buildPath(pathWithQuery: string): string {
  const trimmedPath = pathWithQuery.trim();
  if (!trimmedPath) {
    return API_BASE_PATH;
  }

  const withLeadingSlash = trimmedPath.startsWith("/")
    ? trimmedPath
    : `/${trimmedPath}`;
  return `${API_BASE_PATH}${withLeadingSlash}`;
}

function buildHeaders(init?: HeadersInit): Headers {
  const headers = new Headers(init);
  if (!headers.has("Accept")) {
    headers.set("Accept", "application/json");
  }
  if (API_TOKEN) {
    headers.set("X-API-Token", API_TOKEN);
  }
  return headers;
}

async function readErrorPayload(response: Response): Promise<ApiErrorPayload | null> {
  try {
    return (await response.json()) as ApiErrorPayload;
  } catch {
    return null;
  }
}

async function forkfolioFetch<T>(
  pathWithQuery: string,
  init?: RequestInit,
): Promise<T> {
  const path = buildPath(pathWithQuery);
  const url = `${API_BASE_URL}${path}`;

  const response = await fetch(url, {
    cache: "no-store",
    ...init,
    headers: buildHeaders(init?.headers),
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detail = payload?.detail ?? payload?.error ?? payload?.message ?? null;
    throw new ForkfolioApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

export async function searchRecipes(
  query: string,
  limit = 12,
): Promise<SearchRecipesResponse> {
  const params = new URLSearchParams({
    query: query.trim(),
    limit: String(limit),
  });

  return forkfolioFetch<SearchRecipesResponse>(
    `/recipes/search/semantic?${params.toString()}`,
  );
}

export async function getRecipe(recipeId: string): Promise<GetRecipeResponse> {
  return forkfolioFetch<GetRecipeResponse>(`/recipes/${encodeURIComponent(recipeId)}`);
}

export async function listRecipes(
  limit = 50,
  cursor?: string,
): Promise<ListRecipesResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor?.trim()) {
    params.set("cursor", cursor.trim());
  }
  return forkfolioFetch<ListRecipesResponse>(`/recipes/?${params.toString()}`);
}

export async function listRecipeBooks(
  limit = 50,
): Promise<ListRecipeBooksResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  return forkfolioFetch<ListRecipeBooksResponse>(`/recipe-books/?${params.toString()}`);
}

export async function getRecipeBookByName(name: string): Promise<GetRecipeBookResponse> {
  const params = new URLSearchParams({ name: name.trim() });
  return forkfolioFetch<GetRecipeBookResponse>(`/recipe-books/?${params.toString()}`);
}

export async function getRecipeBook(
  recipeBookId: string,
): Promise<GetRecipeBookResponse> {
  return forkfolioFetch<GetRecipeBookResponse>(
    `/recipe-books/${encodeURIComponent(recipeBookId)}`,
  );
}

export async function createRecipeBook(
  payload: CreateRecipeBookRequest,
): Promise<CreateRecipeBookResponse> {
  return forkfolioFetch<CreateRecipeBookResponse>("/recipe-books/", {
    method: "POST",
    headers: buildHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });
}

export async function getRecipeBookStats(): Promise<GetRecipeBookStatsResponse> {
  return forkfolioFetch<GetRecipeBookStatsResponse>("/recipe-books/stats");
}

export async function getRecipeBooksForRecipe(
  recipeId: string,
): Promise<GetRecipeBooksForRecipeResponse> {
  return forkfolioFetch<GetRecipeBooksForRecipeResponse>(
    `/recipe-books/by-recipe/${encodeURIComponent(recipeId)}`,
  );
}

export async function addRecipeToBook(
  recipeBookId: string,
  recipeId: string,
): Promise<AddRecipeToBookResponse> {
  return forkfolioFetch<AddRecipeToBookResponse>(
    `/recipe-books/${encodeURIComponent(recipeBookId)}/recipes/${encodeURIComponent(recipeId)}`,
    { method: "PUT" },
  );
}

export async function removeRecipeFromBook(
  recipeBookId: string,
  recipeId: string,
): Promise<RemoveRecipeFromBookResponse> {
  return forkfolioFetch<RemoveRecipeFromBookResponse>(
    `/recipe-books/${encodeURIComponent(recipeBookId)}/recipes/${encodeURIComponent(recipeId)}`,
    { method: "DELETE" },
  );
}

export async function processRecipe(
  payload: ProcessRecipeRequest,
): Promise<ProcessRecipeResponse> {
  return forkfolioFetch<ProcessRecipeResponse>("/recipes/process-and-store", {
    method: "POST",
    headers: buildHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });
}

export const processAndStoreRecipe = processRecipe;

export async function previewRecipeFromUrl(
  payload: PreviewRecipeFromUrlRequest,
): Promise<PreviewRecipeFromUrlResponse> {
  return forkfolioFetch<PreviewRecipeFromUrlResponse>("/recipes/preview-from-url", {
    method: "POST",
    headers: buildHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });
}

export type { RecipeRecord };
