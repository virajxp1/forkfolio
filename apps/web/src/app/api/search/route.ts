import { NextRequest, NextResponse } from "next/server";

import { isForkfolioApiError, searchRecipes } from "@/lib/forkfolio-api";
import { getOptionalViewerUserId } from "@/lib/supabase/viewer";

const DEFAULT_LIMIT = 12;
const SEARCH_CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=300";

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

function parseRerank(rawRerank: string | null): boolean {
  if (!rawRerank) {
    return false;
  }

  const normalized = rawRerank.trim().toLowerCase();
  return normalized === "1" || normalized === "true";
}

export async function GET(request: NextRequest) {
  const query = request.nextUrl.searchParams.get("query")?.trim() ?? "";
  const limit = parseLimit(request.nextUrl.searchParams.get("limit"));
  const rerank = parseRerank(request.nextUrl.searchParams.get("rerank"));
  const viewerUserId = await getOptionalViewerUserId();

  if (!query) {
    return NextResponse.json(
      { detail: "Missing query parameter." },
      { status: 400 },
    );
  }

  try {
    const response = await searchRecipes(query, limit, rerank, viewerUserId);
    return NextResponse.json(response, {
      status: 200,
      headers: {
        "Cache-Control": viewerUserId ? "private, no-store" : SEARCH_CACHE_CONTROL,
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
