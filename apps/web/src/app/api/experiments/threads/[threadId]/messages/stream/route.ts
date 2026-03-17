import { NextRequest, NextResponse } from "next/server";

const DEFAULT_API_BASE_URL = "https://forkfolio-be.onrender.com";
const DEFAULT_API_BASE_PATH = "/api/v1";

type ThreadMessageRoutePayload = {
  content?: unknown;
  context_recipe_ids?: unknown;
  attach_recipe_names?: unknown;
};

type NormalizedPayloadResult =
  | {
      payload: {
        content: string;
        context_recipe_ids?: string[];
        attach_recipe_names?: string[];
      };
      status: 200;
    }
  | {
      detail: string;
      status: 400 | 422;
    };

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

function normalizeStringArray(rawValues: unknown): string[] | null {
  if (rawValues === undefined || rawValues === null) {
    return [];
  }
  if (!Array.isArray(rawValues)) {
    return null;
  }

  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const item of rawValues) {
    if (typeof item !== "string") {
      return null;
    }
    const value = item.trim();
    if (!value || seen.has(value)) {
      continue;
    }
    seen.add(value);
    normalized.push(value);
  }
  return normalized;
}

function normalizePayload(payload: ThreadMessageRoutePayload): NormalizedPayloadResult {
  const content = typeof payload.content === "string" ? payload.content.trim() : "";
  if (!content) {
    return { detail: "Missing content in request payload.", status: 400 };
  }

  const contextRecipeIds = normalizeStringArray(payload.context_recipe_ids);
  if (contextRecipeIds === null) {
    return {
      detail: "context_recipe_ids must be an array of strings.",
      status: 400,
    };
  }

  const attachRecipeNames = normalizeStringArray(payload.attach_recipe_names);
  if (attachRecipeNames === null) {
    return {
      detail: "attach_recipe_names must be an array of strings.",
      status: 400,
    };
  }

  return {
    payload: {
      content,
      ...(contextRecipeIds.length ? { context_recipe_ids: contextRecipeIds } : {}),
      ...(attachRecipeNames.length ? { attach_recipe_names: attachRecipeNames } : {}),
    },
    status: 200,
  };
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const payload = (await response.json()) as {
      detail?: string;
      error?: string;
      message?: string;
    };
    return payload.detail ?? payload.error ?? payload.message ?? null;
  } catch {
    return null;
  }
}

function buildUpstreamHeaders(): Headers {
  const headers = new Headers({
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  });
  if (API_TOKEN) {
    headers.set("X-API-Token", API_TOKEN);
  }
  return headers;
}

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ threadId: string }> },
) {
  const { threadId } = await context.params;
  const normalizedThreadId = threadId.trim();
  if (!normalizedThreadId) {
    return NextResponse.json({ detail: "Missing thread id." }, { status: 400 });
  }

  let payload: unknown;
  try {
    payload = (await request.json()) as unknown;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  if (!payload || typeof payload !== "object") {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const normalizedPayload = normalizePayload(payload as ThreadMessageRoutePayload);
  if ("detail" in normalizedPayload) {
    return NextResponse.json(
      { detail: normalizedPayload.detail },
      { status: normalizedPayload.status },
    );
  }

  const upstreamUrl = `${API_BASE_URL}${API_BASE_PATH}/experiments/threads/${encodeURIComponent(
    normalizedThreadId,
  )}/messages/stream`;

  const upstreamResponse = await fetch(upstreamUrl, {
    method: "POST",
    headers: buildUpstreamHeaders(),
    body: JSON.stringify(normalizedPayload.payload),
    cache: "no-store",
  });

  if (!upstreamResponse.ok) {
    const detail = await readErrorDetail(upstreamResponse);
    return NextResponse.json(
      { detail: detail ?? "Failed to create experiment message stream." },
      { status: upstreamResponse.status || 500 },
    );
  }

  if (!upstreamResponse.body) {
    return NextResponse.json(
      { detail: "Streaming response body was empty." },
      { status: 500 },
    );
  }

  return new NextResponse(upstreamResponse.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-store",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
