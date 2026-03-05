import { NextRequest, NextResponse } from "next/server";

import { isForkfolioApiError, processRecipe } from "@/lib/forkfolio-api";
import type { ProcessRecipeRequest } from "@/lib/forkfolio-types";

type ProcessRoutePayload = {
  raw_input?: unknown;
  enforce_deduplication?: unknown;
  isTest?: unknown;
};

function normalizePayload(payload: ProcessRoutePayload): ProcessRecipeRequest | null {
  const rawInput =
    typeof payload.raw_input === "string" ? payload.raw_input.trim() : "";
  if (!rawInput) {
    return null;
  }

  return {
    raw_input: rawInput,
    enforce_deduplication:
      typeof payload.enforce_deduplication === "boolean"
        ? payload.enforce_deduplication
        : true,
    isTest: typeof payload.isTest === "boolean" ? payload.isTest : false,
  };
}

export async function POST(request: NextRequest) {
  let payload: ProcessRoutePayload;
  try {
    payload = (await request.json()) as ProcessRoutePayload;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const normalizedPayload = normalizePayload(payload);
  if (!normalizedPayload) {
    return NextResponse.json(
      { detail: "Missing raw_input in request payload." },
      { status: 400 },
    );
  }

  try {
    const response = await processRecipe(normalizedPayload);
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
      { detail: "Failed to process recipe." },
      { status: 500 },
    );
  }
}
