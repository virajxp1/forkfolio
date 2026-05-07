import { NextRequest, NextResponse } from "next/server";

import { getRecipeBooksForRecipe, isForkfolioApiError } from "@/lib/forkfolio-api";

type RouteContext = {
  params: Promise<{ recipeId: string }>;
};

export async function GET(_request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;

  if (!recipeId?.trim()) {
    return NextResponse.json({ detail: "Missing recipe id." }, { status: 400 });
  }

  try {
    const response = await getRecipeBooksForRecipe(recipeId);
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
      { detail: "Failed to load recipe books for recipe." },
      { status: 500 },
    );
  }
}
