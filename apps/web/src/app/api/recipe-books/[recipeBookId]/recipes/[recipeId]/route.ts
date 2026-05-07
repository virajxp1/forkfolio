import { NextRequest, NextResponse } from "next/server";

import {
  addRecipeToBook,
  isForkfolioApiError,
  removeRecipeFromBook,
} from "@/lib/forkfolio-api";

type RouteContext = {
  params: Promise<{ recipeBookId: string; recipeId: string }>;
};

type ParsedIds =
  | {
      recipeBookId: string;
      recipeId: string;
      status: 200;
    }
  | {
      detail: string;
      status: 400;
    };

async function parseIds(context: RouteContext): Promise<ParsedIds> {
  const { recipeBookId, recipeId } = await context.params;
  const trimmedBookId = recipeBookId?.trim() ?? "";
  const trimmedRecipeId = recipeId?.trim() ?? "";

  if (!trimmedBookId) {
    return { detail: "Missing recipe book id.", status: 400 };
  }

  if (!trimmedRecipeId) {
    return { detail: "Missing recipe id.", status: 400 };
  }

  return {
    recipeBookId: trimmedBookId,
    recipeId: trimmedRecipeId,
    status: 200,
  };
}

export async function PUT(_request: NextRequest, context: RouteContext) {
  const parsedIds = await parseIds(context);
  if ("detail" in parsedIds) {
    return NextResponse.json({ detail: parsedIds.detail }, { status: parsedIds.status });
  }

  try {
    const response = await addRecipeToBook(parsedIds.recipeBookId, parsedIds.recipeId);
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
      { detail: "Failed to add recipe to recipe book." },
      { status: 500 },
    );
  }
}

export async function DELETE(_request: NextRequest, context: RouteContext) {
  const parsedIds = await parseIds(context);
  if ("detail" in parsedIds) {
    return NextResponse.json({ detail: parsedIds.detail }, { status: parsedIds.status });
  }

  try {
    const response = await removeRecipeFromBook(
      parsedIds.recipeBookId,
      parsedIds.recipeId,
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
      { detail: "Failed to remove recipe from recipe book." },
      { status: 500 },
    );
  }
}
