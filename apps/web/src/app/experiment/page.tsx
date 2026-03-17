"use client";

import { History, Loader2, Paperclip, Plus, Send, Sparkles, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type {
  CreateExperimentMessageResponse,
  CreateExperimentThreadResponse,
  ExperimentMessageRecord,
  ExperimentThreadRecord,
  ExperimentThreadSummary,
  GetExperimentThreadResponse,
  ListExperimentThreadsResponse,
  SearchRecipesResponse,
} from "@/lib/forkfolio-types";

type ErrorPayload = {
  detail?: string | { message?: string };
  error?: string;
  message?: string;
};

type RecipeSearchResult = {
  id: string;
  name: string;
};

type AttachmentSelection = {
  id: string;
  name: string;
};

type ParsedSseEvent = {
  event: string;
  data: unknown;
};

const STARTER_PROMPTS = [
  "Invent a new weeknight dinner with at least 30g protein per serving.",
  "Rework chicken tikka masala into a vegan version while keeping it creamy.",
  "Create a gluten-free pasta dish with pantry staples in under 45 minutes.",
];

class BrowserApiError extends Error {
  status: number;

  detail: string | null;

  constructor(message: string, status: number, detail: string | null = null) {
    super(message);
    this.name = "BrowserApiError";
    this.status = status;
    this.detail = detail;
  }
}

function toErrorDetail(payload: ErrorPayload | null): string | null {
  if (!payload) {
    return null;
  }
  if (typeof payload.detail === "string") {
    return payload.detail;
  }
  if (payload.detail && typeof payload.detail === "object") {
    const message = payload.detail.message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  return payload.error ?? payload.message ?? null;
}

async function readErrorPayload(response: Response): Promise<ErrorPayload | null> {
  try {
    return (await response.json()) as ErrorPayload;
  } catch {
    return null;
  }
}

async function browserFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    cache: "no-store",
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detail = toErrorDetail(payload);
    throw new BrowserApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as T;
}

async function listThreadsClient(limit = 40): Promise<ListExperimentThreadsResponse> {
  return browserFetch<ListExperimentThreadsResponse>(`/api/experiments/threads?limit=${limit}`);
}

async function createThreadClient(): Promise<CreateExperimentThreadResponse> {
  return browserFetch<CreateExperimentThreadResponse>("/api/experiments/threads", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  });
}

async function getThreadClient(
  threadId: string,
  messageLimit = 120,
): Promise<GetExperimentThreadResponse> {
  const params = new URLSearchParams({ message_limit: String(messageLimit) });
  return browserFetch<GetExperimentThreadResponse>(
    `/api/experiments/threads/${encodeURIComponent(threadId)}?${params.toString()}`,
  );
}

async function searchRecipesClient(
  query: string,
  signal?: AbortSignal,
): Promise<RecipeSearchResult[]> {
  const params = new URLSearchParams({ query: query.trim(), limit: "10" });
  const response = await browserFetch<SearchRecipesResponse>(
    `/api/search/names?${params.toString()}`,
    { signal },
  );
  const normalized: RecipeSearchResult[] = [];
  for (const item of response.results ?? []) {
    const id = item.id?.trim() ?? "";
    const name = item.name?.trim() ?? "";
    if (!id || !name) {
      continue;
    }
    normalized.push({ id, name });
  }
  return normalized;
}

async function streamMessageClient(
  threadId: string,
  payload: {
    content: string;
    attach_recipe_names?: string[];
  },
): Promise<Response> {
  const response = await fetch(
    `/api/experiments/threads/${encodeURIComponent(threadId)}/messages/stream`,
    {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      },
      cache: "no-store",
      body: JSON.stringify(payload),
    },
  );

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detail = toErrorDetail(payload);
    throw new BrowserApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }
  return response;
}

function formatRole(role: ExperimentMessageRecord["role"]): string {
  if (role === "assistant") {
    return "Assistant";
  }
  if (role === "user") {
    return "You";
  }
  if (role === "tool") {
    return "Tool";
  }
  return "System";
}

function normalizeThread(thread: ExperimentThreadRecord): ExperimentThreadRecord {
  return {
    ...thread,
    messages: Array.isArray(thread.messages) ? thread.messages : [],
    context_recipe_ids: Array.isArray(thread.context_recipe_ids) ? thread.context_recipe_ids : [],
  };
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof BrowserApiError) {
    return error.detail ?? error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

function formatThreadLabel(thread: ExperimentThreadSummary): string {
  const base = thread.title?.trim() ? thread.title.trim() : "Untitled conversation";
  return base.length > 64 ? `${base.slice(0, 61)}...` : base;
}

function formatHistoryPreview(thread: ExperimentThreadSummary): string {
  const text = thread.last_message_content?.trim() ?? "";
  if (!text) {
    return "No messages yet";
  }
  return text.length > 80 ? `${text.slice(0, 77)}...` : text;
}

function toThreadSummary(thread: ExperimentThreadRecord): ExperimentThreadSummary {
  const messages = Array.isArray(thread.messages) ? thread.messages : [];
  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  return {
    id: thread.id,
    mode: thread.mode,
    status: thread.status,
    title: thread.title,
    memory_summary: thread.memory_summary,
    metadata: thread.metadata ?? {},
    created_at: thread.created_at,
    updated_at: thread.updated_at,
    last_message_role: lastMessage?.role ?? null,
    last_message_content: lastMessage?.content ?? null,
    last_message_created_at: lastMessage?.created_at ?? null,
  };
}

function parseSseEvent(block: string): ParsedSseEvent | null {
  const lines = block.split("\n");
  let event = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim() || "message";
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  const dataText = dataLines.join("\n");
  try {
    return { event, data: JSON.parse(dataText) as unknown };
  } catch {
    return { event, data: dataText };
  }
}

function attachmentFeedbackText(payload: {
  attached_recipes?: Array<{ title: string }>;
  unresolved_recipe_names?: string[];
}): string | null {
  const attachedTitles = payload.attached_recipes?.map((item) => item.title) ?? [];
  const unresolved = payload.unresolved_recipe_names ?? [];
  if (!attachedTitles.length && !unresolved.length) {
    return null;
  }
  const attachedPart = attachedTitles.length ? `Attached: ${attachedTitles.join(", ")}.` : "";
  const unresolvedPart = unresolved.length ? ` Not found: ${unresolved.join(", ")}.` : "";
  return `${attachedPart}${unresolvedPart}`.trim();
}

function normalizeSseNewlines(text: string): string {
  return text.replaceAll("\r\n", "\n").replaceAll("\r", "\n");
}

export default function ExperimentPage() {
  const [messageInput, setMessageInput] = useState("");
  const [thread, setThread] = useState<ExperimentThreadRecord | null>(null);
  const [threadHistory, setThreadHistory] = useState<ExperimentThreadSummary[]>([]);
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [isLoadingThread, setIsLoadingThread] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [attachmentFeedback, setAttachmentFeedback] = useState<string | null>(null);
  const [streamStatus, setStreamStatus] = useState<string | null>(null);
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);

  const [pendingAttachments, setPendingAttachments] = useState<AttachmentSelection[]>([]);
  const [isAttachDialogOpen, setIsAttachDialogOpen] = useState(false);
  const [attachSearchInput, setAttachSearchInput] = useState("");
  const [attachSearchResults, setAttachSearchResults] = useState<RecipeSearchResult[]>([]);
  const [isSearchingAttachments, setIsSearchingAttachments] = useState(false);
  const [attachSearchError, setAttachSearchError] = useState<string | null>(null);

  const canSendMessage =
    !isSendingMessage &&
    messageInput.trim().length > 0 &&
    !isCreatingThread &&
    !isLoadingThread;

  async function refreshHistory() {
    setIsLoadingHistory(true);
    try {
      const response = await listThreadsClient(40);
      setThreadHistory(response.threads ?? []);
    } catch {
      setThreadHistory([]);
    } finally {
      setIsLoadingHistory(false);
    }
  }

  function upsertThreadHistory(nextThread: ExperimentThreadRecord) {
    const nextSummary = toThreadSummary(nextThread);
    setThreadHistory((current) => {
      const withoutCurrent = current.filter((item) => item.id !== nextSummary.id);
      return [nextSummary, ...withoutCurrent];
    });
  }

  useEffect(() => {
    void refreshHistory();
  }, []);

  useEffect(() => {
    if (!isAttachDialogOpen) {
      return;
    }
    const query = attachSearchInput.trim();
    if (query.length < 3) {
      setAttachSearchResults([]);
      setAttachSearchError(null);
      setIsSearchingAttachments(false);
      return;
    }

    const controller = new AbortController();
    setIsSearchingAttachments(true);
    setAttachSearchError(null);

    void searchRecipesClient(query, controller.signal)
      .then((results) => {
        setAttachSearchResults(results);
      })
      .catch((error) => {
        if (controller.signal.aborted) {
          return;
        }
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setAttachSearchResults([]);
        setAttachSearchError(getErrorMessage(error, "Failed to search recipes."));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsSearchingAttachments(false);
        }
      });

    return () => {
      controller.abort();
    };
  }, [attachSearchInput, isAttachDialogOpen]);

  async function handleNewThread() {
    setErrorMessage(null);
    setAttachmentFeedback(null);
    setStreamStatus(null);
    setStreamingMessageId(null);
    setPendingAttachments([]);
    setIsCreatingThread(true);

    try {
      const response = await createThreadClient();
      const nextThread = normalizeThread(response.thread);
      setThread(nextThread);
      await refreshHistory();
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to start a new conversation."));
    } finally {
      setIsCreatingThread(false);
    }
  }

  async function handleSelectThread(threadId: string) {
    const normalizedThreadId = threadId.trim();
    if (!normalizedThreadId) {
      return;
    }

    setErrorMessage(null);
    setAttachmentFeedback(null);
    setStreamStatus(null);
    setStreamingMessageId(null);
    setPendingAttachments([]);
    setIsLoadingThread(true);
    try {
      const response = await getThreadClient(normalizedThreadId);
      const nextThread = normalizeThread(response.thread);
      setThread(nextThread);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Failed to load conversation."));
    } finally {
      setIsLoadingThread(false);
    }
  }

  function addPendingAttachment(recipe: RecipeSearchResult) {
    setPendingAttachments((current) => {
      if (current.some((item) => item.id === recipe.id)) {
        return current;
      }
      return [...current, { id: recipe.id, name: recipe.name }];
    });
  }

  function removePendingAttachment(recipeId: string) {
    setPendingAttachments((current) => current.filter((item) => item.id !== recipeId));
  }

  function applyStarterPrompt(prompt: string) {
    setMessageInput(prompt);
    if (!thread && !isCreatingThread && !isLoadingThread) {
      void handleNewThread();
    }
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedMessage = messageInput.trim();
    if (!normalizedMessage) {
      setErrorMessage("Message cannot be empty.");
      return;
    }

    setErrorMessage(null);
    setAttachmentFeedback(null);
    setIsSendingMessage(true);
    setStreamStatus("Drafting response...");
    setStreamingMessageId(null);
    let activeThread = thread;
    if (!activeThread) {
      setStreamStatus("Starting thread...");
      setIsCreatingThread(true);
      try {
        const createResponse = await createThreadClient();
        activeThread = normalizeThread(createResponse.thread);
        setThread(activeThread);
        upsertThreadHistory(activeThread);
        void refreshHistory();
      } catch (error) {
        setErrorMessage(getErrorMessage(error, "Failed to start a new conversation."));
        setIsSendingMessage(false);
        setStreamStatus(null);
        setStreamingMessageId(null);
        return;
      } finally {
        setIsCreatingThread(false);
      }
    }

    const previousThreadSnapshot = activeThread;
    const previousLastSequence = activeThread.messages.reduce(
      (maxValue, message) => Math.max(maxValue, message.sequence_no),
      0,
    );
    const optimisticUserMessage: ExperimentMessageRecord = {
      id: `optimistic-user-${Date.now()}`,
      thread_id: activeThread.id,
      sequence_no: previousLastSequence + 1,
      role: "user",
      content: normalizedMessage,
      tool_name: null,
      tool_call: null,
      created_at: new Date().toISOString(),
    };
    const optimisticAssistantMessageId = `optimistic-assistant-${Date.now()}`;
    const optimisticAssistantMessage: ExperimentMessageRecord = {
      id: optimisticAssistantMessageId,
      thread_id: activeThread.id,
      sequence_no: previousLastSequence + 2,
      role: "assistant",
      content: "",
      tool_name: null,
      tool_call: null,
      created_at: new Date().toISOString(),
    };
    setStreamingMessageId(optimisticAssistantMessageId);
    setThread({
      ...activeThread,
      messages: [...activeThread.messages, optimisticUserMessage, optimisticAssistantMessage],
    });
    const previousAssistantSequence = activeThread.messages.reduce((maxValue, message) => {
      if (message.role !== "assistant") {
        return maxValue;
      }
      return Math.max(maxValue, message.sequence_no);
    }, -1);

    try {
      const response = await streamMessageClient(activeThread.id, {
        content: normalizedMessage,
        ...(pendingAttachments.length
          ? { attach_recipe_names: pendingAttachments.map((item) => item.name) }
          : {}),
      });

      if (!response.body) {
        throw new BrowserApiError("Streaming response body was empty.", 500);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalPayload: CreateExperimentMessageResponse | null = null;
      let streamError: string | null = null;

      const applyStreamEvent = (parsed: ParsedSseEvent) => {
        if (parsed.event === "status") {
          const data = parsed.data as { step?: string };
          if (data?.step) {
            setStreamStatus(data.step === "drafting" ? "Drafting response..." : data.step);
          }
          return;
        }

        if (parsed.event === "delta") {
          const data = parsed.data as { text?: string };
          if (typeof data?.text === "string") {
            setThread((currentThread) => {
              if (!currentThread || currentThread.id !== activeThread.id) {
                return currentThread;
              }
              return {
                ...currentThread,
                messages: currentThread.messages.map((message) =>
                  message.id === optimisticAssistantMessageId
                    ? { ...message, content: `${message.content}${data.text}` }
                    : message,
                ),
              };
            });
          }
          return;
        }

        if (parsed.event === "attachment") {
          const data = parsed.data as {
            attached_recipes?: Array<{ title: string }>;
            unresolved_recipe_names?: string[];
          };
          const text = attachmentFeedbackText(data);
          if (text) {
            setAttachmentFeedback(text);
          }
          return;
        }

        if (parsed.event === "final") {
          finalPayload = parsed.data as CreateExperimentMessageResponse;
          return;
        }

        if (parsed.event === "error") {
          const data = parsed.data as { detail?: string };
          streamError = data?.detail ?? "Failed to stream assistant response.";
        }
      };

      const consumeSseBlocks = () => {
        let delimiterIndex = buffer.indexOf("\n\n");
        while (delimiterIndex >= 0) {
          const block = buffer.slice(0, delimiterIndex);
          buffer = buffer.slice(delimiterIndex + 2);
          delimiterIndex = buffer.indexOf("\n\n");

          const parsed = parseSseEvent(block);
          if (parsed) {
            applyStreamEvent(parsed);
          }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }
        buffer += normalizeSseNewlines(decoder.decode(value, { stream: true }));
        consumeSseBlocks();
      }

      buffer += normalizeSseNewlines(decoder.decode());
      consumeSseBlocks();

      const trailingBlock = buffer.trim();
      if (trailingBlock) {
        const parsed = parseSseEvent(trailingBlock);
        if (parsed) {
          applyStreamEvent(parsed);
        }
      }

      if (streamError) {
        throw new BrowserApiError(streamError, 500, streamError);
      }
      let nextThread: ExperimentThreadRecord | null = null;
      if (finalPayload) {
        nextThread = normalizeThread(finalPayload.thread);
      } else {
        try {
          const fallbackResponse = await getThreadClient(activeThread.id);
          const recoveredThread = normalizeThread(fallbackResponse.thread);
          const hasRecoveredAssistant = recoveredThread.messages.some(
            (message) =>
              message.role === "assistant" && message.sequence_no > previousAssistantSequence,
          );
          if (hasRecoveredAssistant) {
            nextThread = recoveredThread;
          }
        } catch {
          nextThread = null;
        }
      }
      if (!nextThread) {
        throw new BrowserApiError("Stream ended before final payload.", 500);
      }

      setThread(nextThread);
      setMessageInput("");
      setPendingAttachments([]);
      setAttachSearchInput("");
      setAttachSearchResults([]);
      setIsAttachDialogOpen(false);

      if (finalPayload) {
        const finalAttachmentText = attachmentFeedbackText(finalPayload);
        if (finalAttachmentText) {
          setAttachmentFeedback(finalAttachmentText);
        }
      }
      upsertThreadHistory(nextThread);
      void refreshHistory();
    } catch (error) {
      setThread(previousThreadSnapshot);
      setErrorMessage(getErrorMessage(error, "Failed to send message."));
    } finally {
      setIsSendingMessage(false);
      setStreamStatus(null);
      setStreamingMessageId(null);
    }
  }

  const isBusy = isCreatingThread || isLoadingThread || isSendingMessage;
  const normalizedAttachQuery = attachSearchInput.trim();

  return (
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto w-full max-w-7xl space-y-6 px-4 py-8 sm:px-6 sm:py-10">
        <section className="space-y-2">
          <Badge className="rounded-full px-3 py-0.5">Experiment</Badge>
          <h1 className="font-display text-4xl leading-tight sm:text-5xl">
            Recipe Lab
          </h1>
          <p className="max-w-3xl text-base text-muted-foreground">
            Build new ideas or modify existing recipes in one continuous, attach-aware chat thread.
          </p>
        </section>

        <section className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <Card className="h-[75vh]">
            <CardHeader className="space-y-3">
              <CardTitle className="flex items-center gap-2 text-xl">
                <History className="size-4 text-primary" />
                History
              </CardTitle>
              <Button onClick={() => void handleNewThread()} disabled={isCreatingThread}>
                {isCreatingThread ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    Starting…
                  </>
                ) : (
                  <>
                    <Plus className="size-4" />
                    New Thread
                  </>
                )}
              </Button>
            </CardHeader>
            <CardContent className="h-[calc(75vh-8rem)] space-y-2 overflow-y-auto">
              {isLoadingHistory ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : threadHistory.length === 0 ? (
                <p className="text-sm text-muted-foreground">No conversation history yet.</p>
              ) : (
                threadHistory.map((threadItem) => (
                  <button
                    key={threadItem.id}
                    type="button"
                    className={`w-full rounded-md border px-3 py-2 text-left transition-colors ${
                      thread?.id === threadItem.id
                        ? "border-primary/40 bg-primary/5"
                        : "border-border/70 hover:bg-accent/40"
                    }`}
                    onClick={() => void handleSelectThread(threadItem.id)}
                  >
                    <p className="truncate text-sm font-medium">{formatThreadLabel(threadItem)}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {formatHistoryPreview(threadItem)}
                    </p>
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="h-[75vh] overflow-hidden">
            <CardHeader>
              <CardTitle>
                {thread
                  ? thread.title?.trim() || "Untitled conversation"
                  : "Start a new conversation"}
              </CardTitle>
              <CardDescription>
                {thread
                  ? "Continue the thread or attach recipes before your next message."
                  : "Type a message to start instantly, or use New Thread."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex h-[calc(75vh-7.5rem)] min-h-0 flex-col gap-4">
              {errorMessage ? (
                <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {errorMessage}
                </div>
              ) : null}
              {attachmentFeedback ? (
                <div className="rounded-md border border-primary/30 bg-primary/5 px-3 py-2 text-sm text-foreground">
                  {attachmentFeedback}
                </div>
              ) : null}

              <div className="min-h-0 flex-1 overflow-hidden rounded-xl border border-border/70 bg-muted/20">
                {!thread ? (
                  <div className="flex h-full flex-col gap-4 overflow-y-auto p-4 sm:p-5">
                    <div className="rounded-lg border border-border/70 bg-background/90 p-4">
                      <div className="flex items-center gap-2">
                        <span className="rounded-full bg-primary/10 p-2">
                          <Sparkles className="size-4 text-primary" />
                        </span>
                        <p className="text-sm font-semibold">Choose a direction to begin</p>
                      </div>
                      <p className="mt-2 text-sm text-muted-foreground">
                        Quick starters are ready now. Clicking one pre-fills your message and opens
                        a new thread from history.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Quick starters
                      </p>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {STARTER_PROMPTS.map((prompt) => (
                          <button
                            key={prompt}
                            type="button"
                            className="rounded-md border border-border/70 bg-background px-3 py-2 text-left text-sm transition-colors hover:bg-accent/40"
                            onClick={() => applyStarterPrompt(prompt)}
                            disabled={isBusy}
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : thread.messages.length === 0 && !isSendingMessage ? (
                  <div className="flex h-full flex-col gap-4 overflow-y-auto p-4 sm:p-5">
                    <div className="rounded-lg border border-border/70 bg-background/90 p-4">
                      <p className="text-sm font-semibold">Start with a clear goal</p>
                      <p className="mt-1 text-sm text-muted-foreground">
                        Attach a recipe if you want a modification, or just describe the new dish
                        you want to invent.
                      </p>
                    </div>

                    <div className="space-y-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Quick starters
                      </p>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {STARTER_PROMPTS.map((prompt) => (
                          <button
                            key={prompt}
                            type="button"
                            className="rounded-md border border-border/70 bg-background px-3 py-2 text-left text-sm transition-colors hover:bg-accent/40"
                            onClick={() => applyStarterPrompt(prompt)}
                            disabled={isBusy}
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="rounded-lg border border-dashed border-border/80 bg-background/80 p-4 text-sm text-muted-foreground">
                      Attach works like adding reference files to this thread. Anything attached to
                      your next message is preserved in thread context after send.
                    </div>
                  </div>
                ) : (
                  <div className="h-full space-y-3 overflow-y-auto p-3">
                    {thread.messages.map((message) => (
                      <article
                        key={message.id}
                        className="space-y-2 rounded-md border border-border/60 bg-card/40 px-3 py-2"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <Badge variant={message.role === "assistant" ? "default" : "secondary"}>
                            {formatRole(message.role)}
                          </Badge>
                          {isSendingMessage && streamingMessageId === message.id ? (
                            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                              <Loader2 className="size-3 animate-spin" />
                              {streamStatus ?? "Drafting response..."}
                            </span>
                          ) : (
                            <span className="font-mono text-xs text-muted-foreground">
                              #{message.sequence_no}
                            </span>
                          )}
                        </div>
                        <p className="whitespace-pre-wrap text-sm leading-relaxed">
                          {isSendingMessage &&
                          streamingMessageId === message.id &&
                          !message.content.trim()
                            ? "Working on your recipe..."
                            : message.content}
                        </p>
                      </article>
                    ))}
                  </div>
                )}
              </div>

              <form
                className="space-y-3 rounded-lg border border-border/70 bg-card/30 p-3"
                onSubmit={handleSendMessage}
              >
                <div className="space-y-2">
                  <Label htmlFor="message-input">Your message</Label>
                  <Textarea
                    id="message-input"
                    value={messageInput}
                    onChange={(event) => setMessageInput(event.target.value)}
                    placeholder="Attach chicken tikka masala and make it vegan + high protein."
                    className="min-h-24"
                    disabled={isBusy}
                  />
                </div>

                {pendingAttachments.length > 0 ? (
                  <div className="space-y-2">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Attached to next message
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {pendingAttachments.map((attachment) => (
                        <Badge
                          key={attachment.id}
                          variant="secondary"
                          className="inline-flex items-center gap-1"
                        >
                          <span>{attachment.name}</span>
                          <button
                            type="button"
                            className="inline-flex items-center justify-center rounded-sm opacity-80 transition-opacity hover:opacity-100"
                            onClick={() => removePendingAttachment(attachment.id)}
                            aria-label={`Remove ${attachment.name}`}
                          >
                            <X className="size-3" />
                          </button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : null}

                <div className="flex items-center justify-between gap-2">
                  <Dialog open={isAttachDialogOpen} onOpenChange={setIsAttachDialogOpen}>
                    <DialogTrigger asChild>
                      <Button type="button" variant="outline" disabled={isBusy}>
                        <Paperclip className="size-4" />
                        Attach
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-xl gap-0 p-0">
                      <DialogHeader className="border-b px-5 py-4">
                        <DialogTitle>Attach Recipes</DialogTitle>
                        <DialogDescription>
                          Search by recipe name. Add one or more recipes to your next message.
                        </DialogDescription>
                      </DialogHeader>

                      <div className="space-y-4 px-5 py-4">
                        <div className="space-y-2">
                          <Label htmlFor="attach-search-input">Recipe name</Label>
                          <Input
                            id="attach-search-input"
                            value={attachSearchInput}
                            onChange={(event) => setAttachSearchInput(event.target.value)}
                            placeholder="Search chicken tikka masala"
                          />
                          {normalizedAttachQuery.length > 0 && normalizedAttachQuery.length < 3 ? (
                            <p className="text-sm text-muted-foreground">
                              Type at least 3 characters.
                            </p>
                          ) : null}
                          {isSearchingAttachments ? (
                            <p className="text-sm text-muted-foreground">Searching…</p>
                          ) : null}
                          {attachSearchError ? (
                            <p className="text-sm text-destructive">{attachSearchError}</p>
                          ) : null}
                        </div>

                        <div className="rounded-lg border border-border/70 bg-muted/20">
                          <div className="max-h-64 space-y-2 overflow-y-auto p-2">
                            {normalizedAttachQuery.length < 3 ? (
                              <p className="px-2 py-6 text-center text-sm text-muted-foreground">
                                Search with at least 3 characters to attach a recipe.
                              </p>
                            ) : null}
                            {normalizedAttachQuery.length >= 3 &&
                            !isSearchingAttachments &&
                            attachSearchResults.length === 0 &&
                            !attachSearchError ? (
                              <p className="px-2 py-6 text-center text-sm text-muted-foreground">
                                No recipes found for &quot;{normalizedAttachQuery}&quot;.
                              </p>
                            ) : null}
                            {attachSearchResults.map((result) => {
                              const alreadyAttached = pendingAttachments.some(
                                (item) => item.id === result.id,
                              );
                              return (
                                <div
                                  key={result.id}
                                  className="flex items-center justify-between gap-2 rounded-md border border-border/70 bg-background px-3 py-2"
                                >
                                  <div className="min-w-0">
                                    <p className="truncate text-sm font-medium">{result.name}</p>
                                  </div>
                                  <Button
                                    type="button"
                                    size="sm"
                                    variant={alreadyAttached ? "secondary" : "outline"}
                                    disabled={alreadyAttached}
                                    aria-label={`Attach ${result.name}`}
                                    onClick={() => addPendingAttachment(result)}
                                  >
                                    {alreadyAttached ? "Added" : "Attach"}
                                  </Button>
                                </div>
                              );
                            })}
                          </div>
                        </div>

                        <div className="space-y-2">
                          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                            Attached to next message
                          </p>
                          {pendingAttachments.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                              {pendingAttachments.map((attachment) => (
                                <Badge
                                  key={attachment.id}
                                  variant="secondary"
                                  className="inline-flex items-center gap-1"
                                >
                                  <span>{attachment.name}</span>
                                  <button
                                    type="button"
                                    className="inline-flex items-center justify-center rounded-sm opacity-80 transition-opacity hover:opacity-100"
                                    onClick={() => removePendingAttachment(attachment.id)}
                                    aria-label={`Remove ${attachment.name}`}
                                  >
                                    <X className="size-3" />
                                  </button>
                                </Badge>
                              ))}
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">No recipes attached yet.</p>
                          )}
                        </div>
                      </div>

                      <DialogFooter className="border-t px-5 py-3 sm:justify-between">
                        <p className="text-xs text-muted-foreground">
                          {pendingAttachments.length} recipe
                          {pendingAttachments.length === 1 ? "" : "s"} selected
                        </p>
                        <Button type="button" onClick={() => setIsAttachDialogOpen(false)}>
                          Done
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>

                  <Button type="submit" disabled={!canSendMessage}>
                    {isSendingMessage ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Sending…
                      </>
                    ) : (
                      <>
                        <Send className="size-4" />
                        Send
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
