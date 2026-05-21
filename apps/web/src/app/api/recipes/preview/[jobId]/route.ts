import { NextResponse } from "next/server";

import { getRecipePreviewJob, isForkfolioApiError } from "@/lib/forkfolio-api";

export async function GET(
  _request: Request,
  context: { params: Promise<{ jobId: string }> },
) {
  const { jobId } = await context.params;
  const trimmedJobId = jobId?.trim() ?? "";

  if (!trimmedJobId) {
    return NextResponse.json({ detail: "Missing recipe preview job id." }, { status: 400 });
  }

  try {
    const response = await getRecipePreviewJob(trimmedJobId);
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
      { detail: "Failed to load recipe preview job." },
      { status: 500 },
    );
  }
}
