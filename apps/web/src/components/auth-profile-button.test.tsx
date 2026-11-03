import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { setupSupabaseMock } from "@/test/supabase-mock";

const supabaseMock = setupSupabaseMock();

import { AuthProfileButton } from "./auth-profile-button";

describe("AuthProfileButton", () => {
  beforeEach(() => {
    supabaseMock.reset();
  });

  it("treats a missing auth session as a signed-out state instead of an error", async () => {
    supabaseMock.getUserMock.mockResolvedValue({
      data: { user: null },
      error: { message: "Auth session missing!" },
    });

    render(<AuthProfileButton />);

    expect(await screen.findByRole("button", { name: /Sign In/i })).toBeInTheDocument();
    expect(screen.queryByText("Auth session missing!")).not.toBeInTheDocument();
  });

  it("still shows unexpected auth errors", async () => {
    supabaseMock.getUserMock.mockResolvedValue({
      data: { user: null },
      error: { message: "Failed to reach auth service." },
    });

    render(<AuthProfileButton />);

    expect(await screen.findByRole("button", { name: /Sign In/i })).toBeInTheDocument();
    expect(await screen.findByText("Failed to reach auth service.")).toBeInTheDocument();
  });

  it("shows an error when getUser rejects", async () => {
    supabaseMock.getUserMock.mockRejectedValue(new Error("Failed to reach auth service."));

    render(<AuthProfileButton />);

    expect(await screen.findByRole("button", { name: /Sign In/i })).toBeInTheDocument();
    expect(await screen.findByText("Failed to reach auth service.")).toBeInTheDocument();
  });
});
