import { NextRequest, NextResponse } from "next/server";

import { isForkfolioApiError, processRecipe } from "@/lib/forkfolio-api";
import { hasSupabaseAuthConfig } from "@/lib/supabase/config";
import { createClient } from "@/lib/supabase/server";
import {
  MIN_RECIPE_INPUT_LENGTH,
  type ProcessRecipeRequest,
} from "@/lib/forkfolio-types";

type ProcessRoutePayload = {
  raw_input?: unknown;
  source_url?: unknown;
  sourceUrl?: unknown;
  enforce_deduplication?: unknown;
  isPublic?: unknown;
  is_public?: unknown;
  isTest?: unknown;
  is_test?: unknown;
};

type NormalizedPayloadResult =
  | {
      payload: ProcessRecipeRequest;
      status: 200;
    }
  | {
      detail: string;
      status: 400 | 422;
    };

function normalizePayload(payload: ProcessRoutePayload): NormalizedPayloadResult {
  const rawInput =
    typeof payload.raw_input === "string" ? payload.raw_input.trim() : "";
  const rawSourceUrl =
    typeof payload.source_url === "string"
      ? payload.source_url.trim()
      : typeof payload.sourceUrl === "string"
        ? payload.sourceUrl.trim()
        : "";

  if (!rawInput) {
    return {
      detail: "Missing raw_input in request payload.",
      status: 400,
    };
  }

  if (rawInput.length < MIN_RECIPE_INPUT_LENGTH) {
    return {
      detail: `raw_input must be at least ${MIN_RECIPE_INPUT_LENGTH} characters.`,
      status: 422,
    };
  }

  let normalizedSourceUrl: string | undefined;
  if (rawSourceUrl) {
    let parsedUrl: URL;
    try {
      parsedUrl = new URL(rawSourceUrl);
    } catch {
      return {
        detail: "source_url must be a valid URL.",
        status: 422,
      };
    }

    if (!["http:", "https:"].includes(parsedUrl.protocol)) {
      return {
        detail: "source_url must use http or https.",
        status: 422,
      };
    }

    normalizedSourceUrl = parsedUrl.toString();
  }

  const isTestValue =
    typeof payload.isTest === "boolean"
      ? payload.isTest
      : typeof payload.is_test === "boolean"
        ? payload.is_test
        : false;
  const isPublicValue =
    typeof payload.isPublic === "boolean"
      ? payload.isPublic
      : typeof payload.is_public === "boolean"
        ? payload.is_public
        : true;

  return {
    payload: {
      raw_input: rawInput,
      enforce_deduplication:
        typeof payload.enforce_deduplication === "boolean"
          ? payload.enforce_deduplication
          : true,
      is_public: isPublicValue,
      isTest: isTestValue,
      ...(normalizedSourceUrl ? { source_url: normalizedSourceUrl } : {}),
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

  const normalizedPayload = normalizePayload(payload as ProcessRoutePayload);
  if ("detail" in normalizedPayload) {
    return NextResponse.json(
      { detail: normalizedPayload.detail },
      { status: normalizedPayload.status },
    );
  }

  if (!hasSupabaseAuthConfig()) {
    return NextResponse.json(
      { detail: "Recipe creation requires Supabase Auth configuration." },
      { status: 503 },
    );
  }

  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) {
    return NextResponse.json({ detail: "Sign in to create recipes." }, { status: 401 });
  }

  try {
    const response = await processRecipe({
      ...normalizedPayload.payload,
      created_by_user_id: data.user.id,
    });
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

    return NextResponse.json({ detail: "Failed to process recipe." }, { status: 500 });
  }
}
