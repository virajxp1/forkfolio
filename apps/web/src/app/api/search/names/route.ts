import { NextRequest, NextResponse } from "next/server";

import { isForkfolioApiError, searchRecipesByName } from "@/lib/forkfolio-api";
import { getOptionalViewerUserId } from "@/lib/supabase/viewer";

const DEFAULT_LIMIT = 10;
const NAME_SEARCH_CACHE_CONTROL = "public, max-age=15, stale-while-revalidate=60";

function parseLimit(rawLimit: string | null): number {
  if (!rawLimit) {
    return DEFAULT_LIMIT;
  }

  const parsed = Number.parseInt(rawLimit, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_LIMIT;
  }
  return Math.min(parsed, 10);
}

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("query")?.trim() ?? "";
  const limit = parseLimit(request.nextUrl.searchParams.get("limit"));
  const viewerUserId = await getOptionalViewerUserId();

  if (!query) {
    return NextResponse.json(
      { detail: "Missing query parameter." },
      { status: 400 },
    );
  }
  if (query.length < 3) {
    return NextResponse.json(
      { detail: "Query must contain at least 3 characters." },
      { status: 422 },
    );
  }

  try {
    const response = await searchRecipesByName(query, limit, viewerUserId);
    return NextResponse.json(response, {
      status: 200,
      headers: {
        "Cache-Control": viewerUserId ? "private, no-store" : NAME_SEARCH_CACHE_CONTROL,
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
      { detail: "Name search request failed." },
      { status: 500 },
    );
  }
}
