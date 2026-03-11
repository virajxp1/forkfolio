import { NextRequest, NextResponse } from "next/server";

import {
  deleteRecipe,
  getRecipe,
  isForkfolioApiError,
} from "@/lib/forkfolio-api";

const RECIPE_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=900";

type RouteContext = {
  params: Promise<{ recipeId: string }>;
};

type ParsedRecipeId =
  | {
      recipeId: string;
      status: 200;
    }
  | {
      detail: string;
      status: 400;
    };

async function parseRecipeId(context: RouteContext): Promise<ParsedRecipeId> {
  const { recipeId } = await context.params;
  const trimmedRecipeId = recipeId?.trim() ?? "";

  if (!trimmedRecipeId) {
    return { detail: "Missing recipe id.", status: 400 };
  }

  return {
    recipeId: trimmedRecipeId,
    status: 200,
  };
}

export async function GET(_request: NextRequest, context: RouteContext) {
  const parsedRecipeId = await parseRecipeId(context);
  if ("detail" in parsedRecipeId) {
    return NextResponse.json({ detail: parsedRecipeId.detail }, { status: parsedRecipeId.status });
  }

  try {
    const response = await getRecipe(parsedRecipeId.recipeId);
    return NextResponse.json(response, {
      status: 200,
      headers: {
        "Cache-Control": RECIPE_CACHE_CONTROL,
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
      { detail: "Failed to load recipe details." },
      { status: 500 },
    );
  }
}

export async function DELETE(_request: NextRequest, context: RouteContext) {
  const parsedRecipeId = await parseRecipeId(context);
  if ("detail" in parsedRecipeId) {
    return NextResponse.json({ detail: parsedRecipeId.detail }, { status: parsedRecipeId.status });
  }

  try {
    await deleteRecipe(parsedRecipeId.recipeId);
    return NextResponse.json(
      { deleted: true, success: true },
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

    return NextResponse.json({ detail: "Failed to delete recipe." }, { status: 500 });
  }
}
