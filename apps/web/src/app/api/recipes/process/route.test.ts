/** @vitest-environment node */

import { NextRequest } from "next/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { processAndStoreRecipeMock, isForkfolioApiErrorMock } = vi.hoisted(() => ({
  processAndStoreRecipeMock: vi.fn(),
  isForkfolioApiErrorMock: vi.fn(),
}));

vi.mock("@/lib/forkfolio-api", () => ({
  processAndStoreRecipe: processAndStoreRecipeMock,
  isForkfolioApiError: isForkfolioApiErrorMock,
}));

import { POST } from "./route";

describe("POST /api/recipes/process", () => {
  beforeEach(() => {
    processAndStoreRecipeMock.mockReset();
    isForkfolioApiErrorMock.mockReset();
    isForkfolioApiErrorMock.mockReturnValue(false);
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
    expect(await response.json()).toEqual({ detail: "Missing raw_input field." });
    expect(processAndStoreRecipeMock).not.toHaveBeenCalled();
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
    expect(await response.json()).toEqual({ detail: "Invalid JSON body." });
    expect(processAndStoreRecipeMock).not.toHaveBeenCalled();
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
    expect(processAndStoreRecipeMock).not.toHaveBeenCalled();
  });

  it("trims raw_input and forwards request", async () => {
    processAndStoreRecipeMock.mockResolvedValue({
      success: true,
      recipe_id: "recipe-42",
      message: "Recipe processed and stored successfully",
    });

    const request = new NextRequest("http://localhost:3000/api/recipes/process", {
      method: "POST",
      body: JSON.stringify({ raw_input: "  raw recipe text  " }),
      headers: {
        "Content-Type": "application/json",
      },
    });

    const response = await POST(request);

    expect(response.status).toBe(200);
    expect(response.headers.get("Cache-Control")).toBe("no-store");
    expect(processAndStoreRecipeMock).toHaveBeenCalledWith({
      raw_input: "raw recipe text",
    });
  });

  it("maps Forkfolio API errors", async () => {
    const apiError = {
      status: 422,
      detail: "Input too short",
      message: "Input too short",
    };

    processAndStoreRecipeMock.mockRejectedValue(apiError);
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
