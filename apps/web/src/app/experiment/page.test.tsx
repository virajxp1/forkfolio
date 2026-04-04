import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EXPERIMENT_RECIPE_DRAFT_STORAGE_KEY } from "@/lib/experiment-recipe-draft";

import ExperimentPage from "./page";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function sseResponse(events: string): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(encoder.encode(events));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

function toUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") {
    return input;
  }
  if (input instanceof URL) {
    return input.toString();
  }
  return input.url;
}

describe("/experiment page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    window.sessionStorage.clear();
  });

  it("starts a new thread from sidebar and renders active conversation", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input, init) => {
      const url = toUrl(input);
      if (url.startsWith("/api/experiments/threads?")) {
        return jsonResponse({ success: true, count: 0, threads: [] });
      }
      if (url === "/api/experiments/threads" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          thread: {
            id: "thread-1",
            mode: "invent_new",
            title: "Weeknight curry ideas",
            metadata: {},
            context_recipe_ids: [],
            messages: [],
            created_at: null,
            updated_at: null,
          },
        });
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });

    const user = userEvent.setup();
    render(<ExperimentPage />);

    await user.click(screen.getByRole("button", { name: "New Thread" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/experiments/threads",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(await screen.findByText("Weeknight curry ideas")).toBeInTheDocument();
  });

  it("auto-creates a thread when sending the first message from main panel", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input, init) => {
      const url = toUrl(input);
      if (url.startsWith("/api/experiments/threads?")) {
        return jsonResponse({ success: true, count: 0, threads: [] });
      }
      if (url === "/api/experiments/threads" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          thread: {
            id: "thread-auto",
            mode: "invent_new",
            title: null,
            metadata: {},
            context_recipe_ids: [],
            messages: [],
            created_at: null,
            updated_at: null,
          },
        });
      }
      if (
        url === "/api/experiments/threads/thread-auto/messages/stream" &&
        init?.method === "POST"
      ) {
        const finalPayload = {
          thread_id: "thread-auto",
          thread: {
            id: "thread-auto",
            mode: "invent_new",
            title: "Auto start this thread",
            metadata: {},
            context_recipe_ids: [],
            messages: [
              {
                id: "msg-user",
                thread_id: "thread-auto",
                sequence_no: 1,
                role: "user",
                content: "Auto start this thread",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
              {
                id: "msg-assistant",
                thread_id: "thread-auto",
                sequence_no: 2,
                role: "assistant",
                content: "Great, thread created automatically.",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
            ],
            created_at: null,
            updated_at: null,
          },
          user_message: {
            id: "msg-user",
            thread_id: "thread-auto",
            sequence_no: 1,
            role: "user",
            content: "Auto start this thread",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          assistant_message: {
            id: "msg-assistant",
            thread_id: "thread-auto",
            sequence_no: 2,
            role: "assistant",
            content: "Great, thread created automatically.",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          attachment_message: null,
          attached_recipes: [],
          unresolved_recipe_names: [],
          success: true,
        };
        return sseResponse(`event: final\ndata: ${JSON.stringify(finalPayload)}\n\n`);
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });

    const user = userEvent.setup();
    render(<ExperimentPage />);

    await user.type(screen.getByLabelText("Your message"), "Auto start this thread");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/experiments/threads",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/experiments/threads/thread-auto/messages/stream",
      expect.objectContaining({
        method: "POST",
      }),
    );
    expect(await screen.findByText("Great, thread created automatically.")).toBeInTheDocument();
  });

  it("auto-scrolls to the latest message when new messages are added", async () => {
    const scrollIntoViewMock = vi.fn();
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      writable: true,
      value: scrollIntoViewMock,
    });

    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input, init) => {
      const url = toUrl(input);
      if (url.startsWith("/api/experiments/threads?")) {
        return jsonResponse({ success: true, count: 0, threads: [] });
      }
      if (url === "/api/experiments/threads" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          thread: {
            id: "thread-scroll",
            mode: "invent_new",
            title: null,
            metadata: {},
            context_recipe_ids: [],
            messages: [],
            created_at: null,
            updated_at: null,
          },
        });
      }
      if (
        url === "/api/experiments/threads/thread-scroll/messages/stream" &&
        init?.method === "POST"
      ) {
        const finalPayload = {
          thread_id: "thread-scroll",
          thread: {
            id: "thread-scroll",
            mode: "invent_new",
            title: "Scroll check",
            metadata: {},
            context_recipe_ids: [],
            messages: [
              {
                id: "msg-user",
                thread_id: "thread-scroll",
                sequence_no: 1,
                role: "user",
                content: "Check scroll",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
              {
                id: "msg-assistant",
                thread_id: "thread-scroll",
                sequence_no: 2,
                role: "assistant",
                content: "Scrolled to latest message.",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
            ],
            created_at: null,
            updated_at: null,
          },
          user_message: {
            id: "msg-user",
            thread_id: "thread-scroll",
            sequence_no: 1,
            role: "user",
            content: "Check scroll",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          assistant_message: {
            id: "msg-assistant",
            thread_id: "thread-scroll",
            sequence_no: 2,
            role: "assistant",
            content: "Scrolled to latest message.",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          attachment_message: null,
          attached_recipes: [],
          unresolved_recipe_names: [],
          success: true,
        };
        return sseResponse(`event: final\ndata: ${JSON.stringify(finalPayload)}\n\n`);
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });

    const user = userEvent.setup();
    render(<ExperimentPage />);

    await user.type(screen.getByLabelText("Your message"), "Check scroll");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("Scrolled to latest message.")).toBeInTheDocument();
    expect(scrollIntoViewMock).toHaveBeenCalledWith(
      expect.objectContaining({ block: "end", behavior: "smooth" }),
    );
  });

  it("renders assistant markdown in the conversation thread", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input, init) => {
      const url = toUrl(input);
      if (url.startsWith("/api/experiments/threads?")) {
        return jsonResponse({ success: true, count: 0, threads: [] });
      }
      if (url === "/api/experiments/threads" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          thread: {
            id: "thread-markdown",
            mode: "invent_new",
            title: null,
            metadata: {},
            context_recipe_ids: [],
            messages: [],
            created_at: null,
            updated_at: null,
          },
        });
      }
      if (
        url === "/api/experiments/threads/thread-markdown/messages/stream" &&
        init?.method === "POST"
      ) {
        const markdownContent = "### Dinner Plan\n- Turkey chili\n- Zucchini noodles";
        const finalPayload = {
          thread_id: "thread-markdown",
          thread: {
            id: "thread-markdown",
            mode: "invent_new",
            title: "Markdown test",
            metadata: {},
            context_recipe_ids: [],
            messages: [
              {
                id: "msg-user",
                thread_id: "thread-markdown",
                sequence_no: 1,
                role: "user",
                content: "Give me a plan",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
              {
                id: "msg-assistant",
                thread_id: "thread-markdown",
                sequence_no: 2,
                role: "assistant",
                content: markdownContent,
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
            ],
            created_at: null,
            updated_at: null,
          },
          user_message: {
            id: "msg-user",
            thread_id: "thread-markdown",
            sequence_no: 1,
            role: "user",
            content: "Give me a plan",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          assistant_message: {
            id: "msg-assistant",
            thread_id: "thread-markdown",
            sequence_no: 2,
            role: "assistant",
            content: markdownContent,
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          attachment_message: null,
          attached_recipes: [],
          unresolved_recipe_names: [],
          success: true,
        };
        return sseResponse(`event: final\ndata: ${JSON.stringify(finalPayload)}\n\n`);
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });

    const user = userEvent.setup();
    render(<ExperimentPage />);

    await user.type(screen.getByLabelText("Your message"), "Give me a plan");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByRole("heading", { level: 3, name: "Dinner Plan" })).toBeInTheDocument();
    expect(screen.getByRole("list")).toBeInTheDocument();
    expect(screen.queryByText("### Dinner Plan")).not.toBeInTheDocument();
  });

  it("attaches from picker, streams assistant output, and clears chips on send", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input, init) => {
      const url = toUrl(input);
      if (url.startsWith("/api/experiments/threads?")) {
        return jsonResponse({ success: true, count: 0, threads: [] });
      }
      if (url === "/api/experiments/threads" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          thread: {
            id: "thread-1",
            mode: "invent_new",
            title: null,
            metadata: {},
            context_recipe_ids: [],
            messages: [],
            created_at: null,
            updated_at: null,
          },
        });
      }
      if (url.startsWith("/api/search/names?")) {
        return jsonResponse({
          success: true,
          query: "chicken",
          count: 1,
          results: [{ id: "recipe-1", name: "Chicken Tikka Masala", distance: 0.1 }],
        });
      }
      if (url === "/api/experiments/threads/thread-1/messages/stream" && init?.method === "POST") {
        const finalPayload = {
          thread_id: "thread-1",
          thread: {
            id: "thread-1",
            mode: "invent_new",
            title: "Make it vegan",
            metadata: {},
            context_recipe_ids: ["recipe-1"],
            messages: [
              {
                id: "msg-system",
                thread_id: "thread-1",
                sequence_no: 1,
                role: "system",
                content: "Attached recipes: Chicken Tikka Masala.",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
              {
                id: "msg-user",
                thread_id: "thread-1",
                sequence_no: 2,
                role: "user",
                content: "Make it vegan",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
              {
                id: "msg-assistant",
                thread_id: "thread-1",
                sequence_no: 3,
                role: "assistant",
                content: "Use tofu and coconut yogurt for the marinade.",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
            ],
            created_at: null,
            updated_at: null,
          },
          user_message: {
            id: "msg-user",
            thread_id: "thread-1",
            sequence_no: 2,
            role: "user",
            content: "Make it vegan",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          assistant_message: {
            id: "msg-assistant",
            thread_id: "thread-1",
            sequence_no: 3,
            role: "assistant",
            content: "Use tofu and coconut yogurt for the marinade.",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          attachment_message: {
            id: "msg-system",
            thread_id: "thread-1",
            sequence_no: 1,
            role: "system",
            content: "Attached recipes: Chicken Tikka Masala.",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          attached_recipes: [{ id: "recipe-1", title: "Chicken Tikka Masala", created_at: null }],
          unresolved_recipe_names: [],
          success: true,
        };

        return sseResponse(
          [
            'event: status\r\ndata: {"step":"drafting"}\r\n\r\n',
            'event: delta\r\ndata: {"text":"Use tofu and coconut "}\r\n\r\n',
            'event: delta\r\ndata: {"text":"yogurt for the marinade."}\r\n\r\n',
            `event: final\r\ndata: ${JSON.stringify(finalPayload)}`,
          ].join(""),
        );
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });

    const user = userEvent.setup();
    render(<ExperimentPage />);

    await user.click(screen.getByRole("button", { name: "New Thread" }));

    await user.click(screen.getByRole("button", { name: "Attach" }));
    await user.type(screen.getByLabelText("Recipe name"), "chicken");
    expect(await screen.findByText("Chicken Tikka Masala")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Attach Chicken Tikka Masala" }));
    await user.click(screen.getByRole("button", { name: "Done" }));

    expect(await screen.findByLabelText("Remove Chicken Tikka Masala")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Your message"), "Make it vegan");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/experiments/threads/thread-1/messages/stream",
      expect.objectContaining({
        method: "POST",
      }),
    );
    const assistantMatches = await screen.findAllByText(
      "Use tofu and coconut yogurt for the marinade.",
    );
    expect(assistantMatches.length).toBeGreaterThan(0);
    expect(await screen.findByText("Attached: Chicken Tikka Masala.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Remove Chicken Tikka Masala")).not.toBeInTheDocument();
  });

  it("keeps streamed content when final event is missing without reloading thread", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input, init) => {
      const url = toUrl(input);
      if (url.startsWith("/api/experiments/threads?")) {
        return jsonResponse({ success: true, count: 0, threads: [] });
      }
      if (url === "/api/experiments/threads" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          thread: {
            id: "thread-1",
            mode: "invent_new",
            title: "Recover test",
            metadata: {},
            context_recipe_ids: [],
            messages: [],
            created_at: null,
            updated_at: null,
          },
        });
      }
      if (url === "/api/experiments/threads/thread-1/messages/stream" && init?.method === "POST") {
        return sseResponse(
          [
            'event: status\r\ndata: {"step":"drafting"}\r\n\r\n',
            'event: delta\r\ndata: {"text":"Recovered response."}',
          ].join(""),
        );
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });

    const user = userEvent.setup();
    render(<ExperimentPage />);

    await user.click(screen.getByRole("button", { name: "New Thread" }));
    await user.type(screen.getByLabelText("Your message"), "Help me make dinner");
    await user.click(screen.getByRole("button", { name: "Send" }));

    const recoveredMatches = await screen.findAllByText("Recovered response.");
    expect(recoveredMatches.length).toBeGreaterThan(0);
    expect(screen.queryByText("Stream ended before final payload.")).not.toBeInTheDocument();
    const reloadCalls = fetchMock.mock.calls.filter(([input]) =>
      toUrl(input).startsWith("/api/experiments/threads/thread-1?"),
    );
    expect(reloadCalls).toHaveLength(0);
  });

  it("stores latest assistant output before opening Add Recipe flow", async () => {
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockImplementation(async (input, init) => {
      const url = toUrl(input);
      if (url.startsWith("/api/experiments/threads?")) {
        return jsonResponse({ success: true, count: 0, threads: [] });
      }
      if (url === "/api/experiments/threads" && init?.method === "POST") {
        return jsonResponse({
          success: true,
          thread: {
            id: "thread-draft",
            mode: "invent_new",
            title: null,
            metadata: {},
            context_recipe_ids: [],
            messages: [],
            created_at: null,
            updated_at: null,
          },
        });
      }
      if (
        url === "/api/experiments/threads/thread-draft/messages/stream" &&
        init?.method === "POST"
      ) {
        const assistantContent = [
          "Lemon Garlic Chicken",
          "",
          "Ingredients:",
          "- 1 lb chicken thighs",
          "- 2 tbsp olive oil",
          "",
          "Instructions:",
          "1. Season the chicken.",
          "2. Sear and finish in the oven.",
        ].join("\n");
        const finalPayload = {
          thread_id: "thread-draft",
          thread: {
            id: "thread-draft",
            mode: "invent_new",
            title: "Recipe draft",
            metadata: {},
            context_recipe_ids: [],
            messages: [
              {
                id: "msg-user",
                thread_id: "thread-draft",
                sequence_no: 1,
                role: "user",
                content: "Give me a complete recipe draft",
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
              {
                id: "msg-assistant",
                thread_id: "thread-draft",
                sequence_no: 2,
                role: "assistant",
                content: assistantContent,
                tool_name: null,
                tool_call: null,
                created_at: null,
              },
            ],
            created_at: null,
            updated_at: null,
          },
          user_message: {
            id: "msg-user",
            thread_id: "thread-draft",
            sequence_no: 1,
            role: "user",
            content: "Give me a complete recipe draft",
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          assistant_message: {
            id: "msg-assistant",
            thread_id: "thread-draft",
            sequence_no: 2,
            role: "assistant",
            content: assistantContent,
            tool_name: null,
            tool_call: null,
            created_at: null,
          },
          attachment_message: null,
          attached_recipes: [],
          unresolved_recipe_names: [],
          success: true,
        };
        return sseResponse(`event: final\ndata: ${JSON.stringify(finalPayload)}\n\n`);
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });

    const user = userEvent.setup();
    render(<ExperimentPage />);

    await user.type(screen.getByLabelText("Your message"), "Give me a complete recipe draft");
    await user.click(screen.getByRole("button", { name: "Send" }));

    const addAsRecipeLink = await screen.findByRole("link", { name: "Add As Recipe" });
    addAsRecipeLink.addEventListener("click", (event) => event.preventDefault());
    await user.click(addAsRecipeLink);

    expect(window.sessionStorage.getItem(EXPERIMENT_RECIPE_DRAFT_STORAGE_KEY)).toBe(
      [
        "Lemon Garlic Chicken",
        "",
        "Ingredients:",
        "- 1 lb chicken thighs",
        "- 2 tbsp olive oil",
        "",
        "Instructions:",
        "1. Season the chicken.",
        "2. Sear and finish in the oven.",
      ].join("\n"),
    );
  });
});
