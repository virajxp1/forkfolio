/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  processRecipeMock,
  isForkfolioApiErrorMock,
  createClientMock,
  getUserMock,
  hasSupabaseAuthConfigMock,
} = vi.hoisted(() => {
  const processRecipeMock = vi.fn();
  const isForkfolioApiErrorMock = vi.fn();
  const getUserMock = vi.fn();
  const createClientMock = vi.fn(async () => ({
    auth: {
      getUser: getUserMock,
    },
  }));
  const hasSupabaseAuthConfigMock = vi.fn();

  return {
    processRecipeMock,
    isForkfolioApiErrorMock,
    createClientMock,
    getUserMock,
    hasSupabaseAuthConfigMock,
  };
});

vi.mock("@/lib/forkfolio-api", () => ({
  processRecipe: processRecipeMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

vi.mock("@/lib/supabase/server", () => ({
  createClient: createClientMock,
}));

vi.mock("@/lib/supabase/config", () => ({
  hasSupabaseAuthConfig: hasSupabaseAuthConfigMock,
}));

import { POST } from "./route";

describe("POST /api/recipes/process", () => {
  beforeEach(() => {
    processRecipeMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    createClientMock.mockClear();
    getUserMock.mockReset();
    hasSupabaseAuthConfigMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
    hasSupabaseAuthConfigMock.mockReturnValue(true);
    getUserMock.mockResolvedValue({
      data: { user: { id: "user-123" } },
      error: null,
    });
  });

  it("returns 400 when raw_input is missing", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({}),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({
      detail: "Missing raw_input in request payload.",
    });
    expect(processRecipeMock).not.toHaveBeenCalled();
    expect(createClientMock).not.toHaveBeenCalled();
  });

  it("returns 400 when JSON body is not an object", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: "null",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ detail: "Invalid JSON payload." });
    expect(processRecipeMock).not.toHaveBeenCalled();
    expect(createClientMock).not.toHaveBeenCalled();
  });

  it("returns 422 when raw_input is too short", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({ raw_input: "short" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({
      detail: "raw_input must be at least 10 characters.",
    });
    expect(processRecipeMock).not.toHaveBeenCalled();
    expect(createClientMock).not.toHaveBeenCalled();
  });

  it("trims raw_input and forwards request", async () => {
    processRecipeMock.mockResolvedValue({
      success: true,
      recipe_id: "recipe-42",
      created: true,
      message: "Recipe processed and stored successfully",
      recipe: {
        id: "recipe-42",
        title: "Recipe",
        servings: null,
        total_time: null,
        source_url: null,
        is_public: true,
        created_by_user_id: "user-123",
        created_at: null,
        updated_at: null,
        ingredients: [],
        instructions: [],
      },
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({
        raw_input: "  raw recipe text  ",
        source_url: "  https://example.com/recipe  ",
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(processRecipeMock).toHaveBeenCalledWith({
      raw_input: "raw recipe text",
      source_url: "https://example.com/recipe",
      enforce_deduplication: true,
      is_public: true,
      created_by_user_id: "user-123",
      isTest: false,
    });
  });

  it("returns 422 when source_url is invalid", async () => {
    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({
        raw_input: "valid input content",
        source_url: "ftp://example.com/recipe",
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({
      detail: "source_url must use http or https.",
    });
    expect(processRecipeMock).not.toHaveBeenCalled();
    expect(createClientMock).not.toHaveBeenCalled();
  });

  it("returns 503 when Supabase Auth is not configured", async () => {
    hasSupabaseAuthConfigMock.mockReturnValue(false);

    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({ raw_input: "valid input content" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(503);
    expect(await response.json()).toEqual({
      detail: "Recipe creation requires Supabase Auth configuration.",
    });
    expect(createClientMock).not.toHaveBeenCalled();
    expect(processRecipeMock).not.toHaveBeenCalled();
  });

  it("returns 401 when the user is not signed in", async () => {
    getUserMock.mockResolvedValue({
      data: { user: null },
      error: null,
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({ raw_input: "valid input content" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(401);
    expect(await response.json()).toEqual({ detail: "Sign in to create recipes." });
    expect(processRecipeMock).not.toHaveBeenCalled();
  });

  it("forwards private visibility when requested", async () => {
    processRecipeMock.mockResolvedValue({
      success: true,
      recipe_id: "recipe-42",
      created: true,
      recipe: {
        id: "recipe-42",
        title: "Recipe",
        servings: null,
        total_time: null,
        source_url: null,
        is_public: false,
        created_by_user_id: "user-123",
        created_at: null,
        updated_at: null,
        ingredients: [],
        instructions: [],
      },
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({
        raw_input: "valid input content",
        isPublic: false,
      }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(processRecipeMock).toHaveBeenCalledWith({
      raw_input: "valid input content",
      enforce_deduplication: true,
      is_public: false,
      created_by_user_id: "user-123",
      isTest: false,
    });
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 422,
      detail: "Input too short",
      message: "Input too short",
    };

    processRecipeMock.mockRejectedValue(apiError);
    isForkfolioApiErrorMock.mockImplementation((error: unknown) => error === apiError);

    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({ raw_input: "valid input content" }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({ detail: "Input too short" });
  });
});
