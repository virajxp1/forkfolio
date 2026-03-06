import { NextRequest, NextResponse } from "next/server";

import {
  isForkfolioApiError,
  processAndStoreRecipe,
} from "@/lib/forkfolio-api";
import {
  MIN_RECIPE_INPUT_LENGTH,
  type ProcessRecipeRequest,
} from "@/lib/forkfolio-types";

type ProcessRequestBody = {
  raw_input?: unknown;
  enforce_deduplication?: unknown;
  isTest?: unknown;
  is_test?: unknown;
};

function parseBoolean(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined;
}

function getRawInput(payload: ProcessRequestBody): string {
  if (typeof payload.raw_input !== "string") {
    return "";
  }
  return payload.raw_input.trim();
}

export async function POST(request: NextRequest) {
  let payload: unknown;

  try {
    payload = (await request.json()) as unknown;
  } catch {
    return NextResponse.json(
      { detail: "Invalid JSON body." },
      { status: 400 },
    );
  }

  if (!payload || typeof payload !== "object") {
    return NextResponse.json(
      { detail: "Invalid JSON body." },
      { status: 400 },
    );
  }

  const normalizedPayload = payload as ProcessRequestBody;
  const rawInput = getRawInput(normalizedPayload);
  if (!rawInput) {
    return NextResponse.json(
      { detail: "Missing raw_input field." },
      { status: 400 },
    );
  }
  if (rawInput.length < MIN_RECIPE_INPUT_LENGTH) {
    return NextResponse.json(
      {
        detail: `raw_input must be at least ${MIN_RECIPE_INPUT_LENGTH} characters.`,
      },
      { status: 422 },
    );
  }

  const processPayload: ProcessRecipeRequest = {
    raw_input: rawInput,
  };

  const enforceDeduplication = parseBoolean(normalizedPayload.enforce_deduplication);
  if (enforceDeduplication !== undefined) {
    processPayload.enforce_deduplication = enforceDeduplication;
  }

  const isTest = parseBoolean(normalizedPayload.isTest);
  if (isTest !== undefined) {
    processPayload.isTest = isTest;
  }

  const isTestUnderscored = parseBoolean(normalizedPayload.is_test);
  if (isTestUnderscored !== undefined) {
    processPayload.is_test = isTestUnderscored;
  }

  try {
    const response = await processAndStoreRecipe(processPayload);
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
      { detail: "Recipe processing request failed." },
      { status: 500 },
    );
  }
}
