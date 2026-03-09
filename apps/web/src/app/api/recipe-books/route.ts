import { NextRequest, NextResponse } from "next/server";

import {
  createRecipeBook,
  getRecipeBookByName,
  isForkfolioApiError,
  listRecipeBooks,
} from "@/lib/forkfolio-api";

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;
const MAX_NAME_LENGTH = 120;
const MAX_DESCRIPTION_LENGTH = 1000;

type CreateRoutePayload = {
  name?: unknown;
  description?: unknown;
};

type NormalizedCreatePayload =
  | {
      payload: {
        name: string;
        description: string | null;
      };
      status: 200;
    }
  | {
      detail: string;
      status: 400 | 422;
    };

function parseLimit(rawLimit: string | null): number {
  if (!rawLimit) {
    return DEFAULT_LIMIT;
  }

  const parsed = Number.parseInt(rawLimit, 10);
  if (!Number.isFinite(parsed) || parsed < 1) {
    return DEFAULT_LIMIT;
  }

  return Math.min(parsed, MAX_LIMIT);
}

function normalizeCreatePayload(payload: CreateRoutePayload): NormalizedCreatePayload {
  const name = typeof payload.name === "string" ? payload.name.trim() : "";
  if (!name) {
    return {
      detail: "Missing name in request payload.",
      status: 400,
    };
  }

  if (name.length > MAX_NAME_LENGTH) {
    return {
      detail: `name must be at most ${MAX_NAME_LENGTH} characters.`,
      status: 422,
    };
  }

  if (
    payload.description !== undefined &&
    payload.description !== null &&
    typeof payload.description !== "string"
  ) {
    return {
      detail: "description must be a string.",
      status: 400,
    };
  }

  const description =
    typeof payload.description === "string" ? payload.description.trim() : null;
  if (description && description.length > MAX_DESCRIPTION_LENGTH) {
    return {
      detail: `description must be at most ${MAX_DESCRIPTION_LENGTH} characters.`,
      status: 422,
    };
  }

  return {
    payload: {
      name,
      description,
    },
    status: 200,
  };
}

export async function GET(request: NextRequest) {
  const name = request.nextUrl.searchParams.get("name")?.trim() ?? "";
  const limit = parseLimit(request.nextUrl.searchParams.get("limit"));

  try {
    const response = name
      ? await getRecipeBookByName(name)
      : await listRecipeBooks(limit);

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
      { detail: "Failed to load recipe books." },
      { status: 500 },
    );
  }
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

  const normalizedPayload = normalizeCreatePayload(payload as CreateRoutePayload);
  if ("detail" in normalizedPayload) {
    return NextResponse.json(
      { detail: normalizedPayload.detail },
      { status: normalizedPayload.status },
    );
  }

  try {
    const response = await createRecipeBook(normalizedPayload.payload);
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
      { detail: "Failed to create recipe book." },
      { status: 500 },
    );
  }
}
