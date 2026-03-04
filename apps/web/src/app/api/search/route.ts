import { NextRequest, NextResponse } from "next/server";

import { isForkfolioApiError, searchRecipes } from "@/lib/forkfolio-api";

const DEFAULT_LIMIT = 12;

function parseLimit(rawLimit: string | null): number {
  if (!rawLimit) {
    return DEFAULT_LIMIT;
  }

  const parsed = Number.parseInt(rawLimit, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_LIMIT;
  }
  return Math.min(parsed, 50);
}

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("query")?.trim() ?? "";
  const limit = parseLimit(request.nextUrl.searchParams.get("limit"));

  if (!query) {
    return NextResponse.json(
      { detail: "Missing query parameter." },
      { status: 400 },
    );
  }

  try {
    const response = await searchRecipes(query, limit);
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
      { detail: "Search request failed." },
      { status: 500 },
    );
  }
}
