import { NextRequest, NextResponse } from "next/server";

import { getRecipe, isForkfolioApiError } from "@/lib/forkfolio-api";

const RECIPE_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=900";

type RouteContext = {
  params: Promise<{ recipeId: string }>;
};

export async function GET(_request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;

  if (!recipeId?.trim()) {
    return NextResponse.json(
      { detail: "Missing recipe id." },
      { status: 400 },
    );
  }

  try {
    const response = await getRecipe(recipeId);
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
