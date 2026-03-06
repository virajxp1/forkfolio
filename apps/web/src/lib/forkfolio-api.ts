import type {
  GetRecipeResponse,
  ProcessRecipeRequest,
  ProcessRecipeResponse,
  RecipeRecord,
  SearchRecipesResponse,
} from "@/lib/forkfolio-types";

const DEFAULT_API_BASE_URL = "https://forkfolio-be.onrender.com";
const DEFAULT_API_BASE_PATH = "/api/v1";

type ApiErrorPayload = {
  detail?: string;
  error?: string;
  message?: string;
};

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

function getApiBaseUrl(): string {
  return process.env.FORKFOLIO_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL;
}

function getApiBasePath(): string {
  const configured = process.env.FORKFOLIO_API_BASE_PATH?.trim() || DEFAULT_API_BASE_PATH;
  if (configured.startsWith("/")) {
    return configured;
  }
  return `/${configured}`;
}

function buildApiUrl(pathname: string): URL {
  const normalizedPathname = pathname.startsWith("/") ? pathname : `/${pathname}`;
  const baseUrl = new URL(getApiBaseUrl());
  baseUrl.pathname = `${getApiBasePath().replace(/\/$/, "")}${normalizedPathname}`;
  return baseUrl;
}

async function parseErrorPayload(response: Response): Promise<ApiErrorPayload | null> {
  try {
    return (await response.json()) as ApiErrorPayload;
  } catch {
    return null;
  }
}

async function requestForkfolio<T>(
  pathname: string,
  init: RequestInit = {},
): Promise<T> {
  const url = buildApiUrl(pathname);
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const token = process.env.FORKFOLIO_API_TOKEN?.trim();
  if (token) {
    headers.set("X-API-Token", token);
  }

  const response = await fetch(url, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    const payload = await parseErrorPayload(response);
    const detail = payload?.detail ?? payload?.error ?? payload?.message ?? null;
    throw new ForkfolioApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

export function searchRecipes(
  query: string,
  limit: number,
): Promise<SearchRecipesResponse> {
  const params = new URLSearchParams({ query, limit: String(limit) });
  return requestForkfolio<SearchRecipesResponse>(
    `/recipes/search/semantic?${params.toString()}`,
  );
}

export function getRecipe(recipeId: string): Promise<GetRecipeResponse> {
  return requestForkfolio<GetRecipeResponse>(`/recipes/${encodeURIComponent(recipeId)}`);
}

export function processAndStoreRecipe(
  payload: ProcessRecipeRequest,
): Promise<ProcessRecipeResponse> {
  return requestForkfolio<ProcessRecipeResponse>("/recipes/process-and-store", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type { RecipeRecord };
