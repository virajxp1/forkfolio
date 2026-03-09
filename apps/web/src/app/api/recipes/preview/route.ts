import { NextRequest, NextResponse } from "next/server";

import { isForkfolioApiError, previewRecipeFromUrl } from "@/lib/forkfolio-api";
import type { PreviewRecipeFromUrlRequest } from "@/lib/forkfolio-types";

type PreviewRoutePayload = {
  url?: unknown;
};

type NormalizedPayloadResult =
  | {
      payload: PreviewRecipeFromUrlRequest;
      status: 200;
    }
  | {
      detail: string;
      status: 400 | 422;
    };

function normalizePayload(payload: PreviewRoutePayload): NormalizedPayloadResult {
  const rawUrl = typeof payload.url === "string" ? payload.url.trim() : "";

  if (!rawUrl) {
    return {
      detail: "Missing url in request payload.",
      status: 400,
    };
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(rawUrl);
  } catch {
    return {
      detail: "url must be a valid URL.",
      status: 422,
    };
  }

  if (!["http:", "https:"].includes(parsedUrl.protocol)) {
    return {
      detail: "url must use http or https.",
      status: 422,
    };
  }

  return {
    payload: { url: parsedUrl.toString() },
    status: 200,
  };
}

export async function POST(request: NextRequest) {
  let payload: unknown;

  try {
    payload = (await request.json()) as unknown;
  } catch {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  if (!payload || typeof payload !== "object") {
    return NextResponse.json({ detail: "Invalid JSON payload." }, { status: 400 });
  }

  const normalizedPayload = normalizePayload(payload as PreviewRoutePayload);
  if ("detail" in normalizedPayload) {
    return NextResponse.json(
      { detail: normalizedPayload.detail },
      { status: normalizedPayload.status },
    );
  }

  try {
    const response = await previewRecipeFromUrl(normalizedPayload.payload);
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
      { detail: "Failed to preview recipe from URL." },
      { status: 500 },
    );
  }
}
