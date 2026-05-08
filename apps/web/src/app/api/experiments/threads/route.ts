import { NextRequest, NextResponse } from "next/server";

import {
  createExperimentThread,
  isForkfolioApiError,
  listExperimentThreads,
} from "@/lib/forkfolio-api";
import { getRequiredViewerUserId } from "@/lib/supabase/viewer";
import type {
  CreateExperimentThreadRequest,
  ExperimentThreadSummary,
} from "@/lib/forkfolio-types";

type ThreadsRoutePayload = {
  title?: unknown;
  context_recipe_ids?: unknown;
  is_test?: unknown;
  isTest?: unknown;
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

const TEST_THREAD_TITLE_PATTERN =
  /\b(e2e|pytest|playwright|cypress|integration[-_\s]?test|smoke[-_\s]?test)\b/i;
const TRUTHY_FLAG_VALUES = new Set(["1", "true", "yes", "y", "on"]);
const TEST_METADATA_FLAG_KEYS = ["is_test", "isTest", "test", "is_e2e", "e2e"];
const TEST_METADATA_SOURCE_KEYS = [
  "source",
  "origin",
  "env",
  "environment",
  "category",
  "tag",
  "type",
];
const TEST_METADATA_SOURCE_VALUES = new Set([
  "test",
  "e2e",
  "pytest",
  "playwright",
  "cypress",
  "integration-test",
  "integration_test",
  "smoke-test",
  "smoke_test",
  "ci",
]);

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

function parseIncludeTest(rawIncludeTest: string | null): boolean {
  if (!rawIncludeTest) {
    return false;
  }
  return TRUTHY_FLAG_VALUES.has(rawIncludeTest.trim().toLowerCase());
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
  const contextRecipeIds = normalizeContextRecipeIds(payload.context_recipe_ids);
  if (contextRecipeIds === null) {
    return {
      detail: "context_recipe_ids must be an array of strings.",
      status: 400,
    };
  }

  const title =
    typeof payload.title === "string" && payload.title.trim() ? payload.title.trim() : undefined;
  const isTestRaw = payload.is_test ?? payload.isTest;
  let isTest: boolean | undefined;
  if (isTestRaw !== undefined && isTestRaw !== null) {
    if (typeof isTestRaw !== "boolean") {
      return {
        detail: "is_test must be a boolean when provided.",
        status: 400,
      };
    }
    isTest = isTestRaw;
  }

  return {
    payload: {
      ...(title ? { title } : {}),
      ...(contextRecipeIds.length ? { context_recipe_ids: contextRecipeIds } : {}),
      ...(isTest === true ? { is_test: true } : {}),
    },
    status: 200,
  };
}

function isTruthyFlag(value: unknown): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value === "number") {
    return value === 1;
  }
  if (typeof value === "string") {
    return TRUTHY_FLAG_VALUES.has(value.trim().toLowerCase());
  }
  return false;
}

function isTestThread(thread: ExperimentThreadSummary): boolean {
  const metadataRaw = thread.metadata;
  const metadata =
    metadataRaw && typeof metadataRaw === "object"
      ? (metadataRaw as Record<string, unknown>)
      : {};
  for (const key of TEST_METADATA_FLAG_KEYS) {
    if (isTruthyFlag(metadata[key])) {
      return true;
    }
  }
  for (const key of TEST_METADATA_SOURCE_KEYS) {
    const value = metadata[key];
    if (
      typeof value === "string" &&
      TEST_METADATA_SOURCE_VALUES.has(value.trim().toLowerCase())
    ) {
      return true;
    }
  }
  const title = typeof thread.title === "string" ? thread.title : "";
  return TEST_THREAD_TITLE_PATTERN.test(title);
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

  const viewerResult = await getRequiredViewerUserId(
    "Experiment threads",
    "Sign in to use experiment threads.",
  );
  if (!viewerResult.viewerUserId) {
    return NextResponse.json(
      { detail: viewerResult.detail },
      { status: viewerResult.status },
    );
  }

  try {
    const response = await createExperimentThread(
      normalizedPayload.payload,
      viewerResult.viewerUserId,
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
      { detail: "Failed to create experiment thread." },
      { status: 500 },
    );
  }
}

export async function GET(request: NextRequest) {
  const limit = parseLimit(request.nextUrl.searchParams.get("limit"));
  const includeTest = parseIncludeTest(
    request.nextUrl.searchParams.get("include_test"),
  );
  const viewerResult = await getRequiredViewerUserId(
    "Experiment threads",
    "Sign in to use experiment threads.",
  );
  if (!viewerResult.viewerUserId) {
    return NextResponse.json(
      { detail: viewerResult.detail },
      { status: viewerResult.status },
    );
  }
  try {
    const response = await listExperimentThreads(
      limit,
      includeTest,
      viewerResult.viewerUserId,
    );
    const listedThreads = Array.isArray(response.threads) ? response.threads : [];
    const filteredThreads = includeTest
      ? listedThreads.slice(0, limit)
      : listedThreads.filter((thread) => !isTestThread(thread)).slice(0, limit);

    return NextResponse.json(
      {
        ...response,
        threads: filteredThreads,
        count: filteredThreads.length,
      },
      {
        status: 200,
        headers: {
          "Cache-Control": "no-store",
        },
      },
    );
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
