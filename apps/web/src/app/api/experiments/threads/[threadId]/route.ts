import { NextRequest, NextResponse } from "next/server";

import { getExperimentThread, isForkfolioApiError } from "@/lib/forkfolio-api";

const DEFAULT_MESSAGE_LIMIT = 120;

function parseMessageLimit(rawMessageLimit: string | null): number {
  if (!rawMessageLimit) {
    return DEFAULT_MESSAGE_LIMIT;
  }

  const parsed = Number.parseInt(rawMessageLimit, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_MESSAGE_LIMIT;
  }
  return Math.min(parsed, 500);
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ threadId: string }> },
) {
  const { threadId } = await context.params;
  const normalizedThreadId = threadId.trim();
  if (!normalizedThreadId) {
    return NextResponse.json({ detail: "Missing thread id." }, { status: 400 });
  }

  const messageLimit = parseMessageLimit(request.nextUrl.searchParams.get("message_limit"));

  try {
    const response = await getExperimentThread(normalizedThreadId, messageLimit);
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
      { detail: "Failed to get experiment thread." },
      { status: 500 },
    );
  }
}
