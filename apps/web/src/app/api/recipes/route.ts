import { NextRequest, NextResponse } from "next/server";

import { isForkfolioApiError, listRecipes } from "@/lib/forkfolio-api";
import { getOptionalViewerUserId } from "@/lib/supabase/viewer";

const DEFAULT_LIMIT = 12;
const RECIPES_CACHE_CONTROL = "public, max-age=60, stale-while-revalidate=300";

function parseLimit(rawLimit: string | null): number {
  if (!rawLimit) {
    return DEFAULT_LIMIT;
  }

  const parsed = Number.parseInt(rawLimit, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_LIMIT;
  }
  return Math.min(parsed, 200);
}

export async function GET(request: NextRequest) {
  const limit = parseLimit(request.nextUrl.searchParams.get("limit"));
  const rawCursor = request.nextUrl.searchParams.get("cursor");
  const cursor = rawCursor?.trim() ? rawCursor.trim() : undefined;
  const viewerUserId = await getOptionalViewerUserId();

  try {
    const response = await listRecipes(limit, cursor, viewerUserId);
    return NextResponse.json(response, {
      status: 200,
      headers: {
        "Cache-Control": viewerUserId ? "private, no-store" : RECIPES_CACHE_CONTROL,
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
      { detail: "Failed to list recipes." },
      { status: 500 },
    );
  }
}
