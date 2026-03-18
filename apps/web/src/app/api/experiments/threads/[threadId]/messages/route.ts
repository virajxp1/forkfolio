import { NextRequest, NextResponse } from "next/server";

import { createExperimentMessage, isForkfolioApiError } from "@/lib/forkfolio-api";
import type { CreateExperimentMessageRequest } from "@/lib/forkfolio-types";

type ThreadMessageRoutePayload = {
  content?: unknown;
  context_recipe_ids?: unknown;
  attach_recipe_ids?: unknown;
  attach_recipe_names?: unknown;
};

type NormalizedPayloadResult =
  | {
      payload: CreateExperimentMessageRequest;
      status: 200;
    }
  | {
      detail: string;
      status: 400 | 422;
    };

function normalizeContextRecipeIds(rawContextIds: unknown): string[] | null {
  if (rawContextIds === undefined || rawContextIds === null) {
    return [];
  }
  if (!Array.isArray(rawContextIds)) {
    return null;
  }

  const seen = new Set<string>();
  const normalized: string[] = [];
  for (const item of rawContextIds) {
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

  const contextRecipeIds = normalizeContextRecipeIds(payload.context_recipe_ids);
  if (contextRecipeIds === null) {
    return {
      detail: "context_recipe_ids must be an array of strings.",
      status: 400,
    };
  }

  const attachRecipeNames = normalizeContextRecipeIds(payload.attach_recipe_names);
  if (attachRecipeNames === null) {
    return {
      detail: "attach_recipe_names must be an array of strings.",
      status: 400,
    };
  }
  const attachRecipeIds = normalizeContextRecipeIds(payload.attach_recipe_ids);
  if (attachRecipeIds === null) {
    return {
      detail: "attach_recipe_ids must be an array of strings.",
      status: 400,
    };
  }

  return {
    payload: {
      content,
      ...(contextRecipeIds.length ? { context_recipe_ids: contextRecipeIds } : {}),
      ...(attachRecipeIds.length ? { attach_recipe_ids: attachRecipeIds } : {}),
      ...(attachRecipeNames.length ? { attach_recipe_names: attachRecipeNames } : {}),
    },
    status: 200,
  };
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

  try {
    const response = await createExperimentMessage(
      normalizedThreadId,
      normalizedPayload.payload,
    );
    return NextResponse.json(response, {
      status: 200,
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    if (isForkfolioApiError(error)) {
      return NextResponse.json(
        { detail: error.detail ?? error.message },
        { status: error.status },
      );
    }

    return NextResponse.json(
      { detail: "Failed to create experiment message." },
      { status: 500 },
    );
  }
}
