import { NextRequest, NextResponse } from "next/server";

import {
  createExperimentThread,
  isForkfolioApiError,
  listExperimentThreads,
} from "@/lib/forkfolio-api";
import type {
  CreateExperimentThreadRequest,
  ExperimentMode,
} from "@/lib/forkfolio-types";

type ThreadsRoutePayload = {
  mode?: unknown;
  title?: unknown;
  context_recipe_ids?: unknown;
};

type NormalizedPayloadResult =
  | {
      payload: CreateExperimentThreadRequest;
      status: 200;
    }
  | {
      detail: string;
      status: 400 | 422;
    };

function parseLimit(rawLimit: string | null): number {
  if (!rawLimit) {
    return 20;
  }
  const parsed = Number.parseInt(rawLimit, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return 20;
  }
  return Math.min(parsed, 100);
}

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

function normalizePayload(payload: ThreadsRoutePayload): NormalizedPayloadResult {
  const modeRaw = typeof payload.mode === "string" ? payload.mode.trim() : "invent_new";
  if (!modeRaw) {
    return {
      detail: "mode must be one of: invent_new, modify_existing.",
      status: 422,
    };
  }
  const mode = modeRaw as ExperimentMode;
  if (mode !== "invent_new" && mode !== "modify_existing") {
    return {
      detail: "mode must be one of: invent_new, modify_existing.",
      status: 422,
    };
  }

  const contextRecipeIds = normalizeContextRecipeIds(payload.context_recipe_ids);
  if (contextRecipeIds === null) {
    return {
      detail: "context_recipe_ids must be an array of strings.",
      status: 400,
    };
  }

  const title =
    typeof payload.title === "string" && payload.title.trim() ? payload.title.trim() : undefined;

  return {
    payload: {
      mode,
      ...(title ? { title } : {}),
      ...(contextRecipeIds.length ? { context_recipe_ids: contextRecipeIds } : {}),
    },
    status: 200,
  };
}

export async function POST(request: NextRequest) {
  let payload: unknown;

  try {
    payload = (await request.json()) as unknown;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  if (!payload || typeof payload !== "object") {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const normalizedPayload = normalizePayload(payload as ThreadsRoutePayload);
  if ("detail" in normalizedPayload) {
    return NextResponse.json(
      { detail: normalizedPayload.detail },
      { status: normalizedPayload.status },
    );
  }

  try {
    const response = await createExperimentThread(normalizedPayload.payload);
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
      { detail: "Failed to create experiment thread." },
      { status: 500 },
    );
  }
}

export async function GET(request: NextRequest) {
  const limit = parseLimit(request.nextUrl.searchParams.get("limit"));
  try {
    const response = await listExperimentThreads(limit);
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
      { detail: "Failed to list experiment threads." },
      { status: 500 },
    );
  }
}
