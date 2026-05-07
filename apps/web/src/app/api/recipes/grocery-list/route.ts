import { NextRequest, NextResponse } from "next/server";

import { createGroceryList, isForkfolioApiError } from "@/lib/forkfolio-api";
import type { CreateGroceryListRequest } from "@/lib/forkfolio-types";

const MAX_RECIPE_IDS = 100;

type GroceryListRoutePayload = {
  recipe_ids?: unknown;
};

type NormalizedPayloadResult =
  | {
      payload: CreateGroceryListRequest;
      status: 200;
    }
  | {
      detail: string;
      status: 400 | 422;
    };

function normalizePayload(payload: GroceryListRoutePayload): NormalizedPayloadResult {
  if (!Array.isArray(payload.recipe_ids)) {
    return {
      detail: "recipe_ids must be a non-empty array of recipe IDs.",
      status: 400,
    };
  }

  const recipeIds = payload.recipe_ids
    .map((value) => (typeof value === "string" ? value.trim() : ""))
    .filter((value) => value.length > 0);

  const uniqueRecipeIds = [...new Set(recipeIds)];
  if (!uniqueRecipeIds.length) {
    return {
      detail: "recipe_ids must include at least one recipe ID.",
      status: 422,
    };
  }

  if (uniqueRecipeIds.length > MAX_RECIPE_IDS) {
    return {
      detail: `recipe_ids cannot exceed ${MAX_RECIPE_IDS} entries.`,
      status: 422,
    };
  }

  return {
    payload: {
      recipe_ids: uniqueRecipeIds,
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

  const normalizedPayload = normalizePayload(payload as GroceryListRoutePayload);
  if ("detail" in normalizedPayload) {
    return NextResponse.json(
      { detail: normalizedPayload.detail },
      { status: normalizedPayload.status },
    );
  }

  try {
    const response = await createGroceryList(normalizedPayload.payload);
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
      { detail: "Failed to generate grocery list." },
      { status: 500 },
    );
  }
}
