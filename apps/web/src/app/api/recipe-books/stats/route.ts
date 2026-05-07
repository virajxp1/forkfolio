import { NextResponse } from "next/server";

import { getRecipeBookStats, isForkfolioApiError } from "@/lib/forkfolio-api";

export async function GET() {
  try {
    const response = await getRecipeBookStats();
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
      { detail: "Failed to load recipe book stats." },
      { status: 500 },
    );
  }
}
