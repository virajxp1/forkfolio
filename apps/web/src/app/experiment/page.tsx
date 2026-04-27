"use client";

import { useRouter } from "next/navigation";
import type { User } from "@supabase/supabase-js";
import {
  History,
  Loader2,
  LockKeyhole,
  Paperclip,
  Plus,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import {
  type FormEvent,
  type ReactNode,
  useEffect,
  useEffectEvent,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { AuthProfileButton } from "@/components/auth-profile-button";
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
import { saveExperimentRecipeDraft } from "@/lib/experiment-recipe-draft";
import { isExpectedSignedOutMessage } from "@/lib/supabase/auth";
import { createClient as createSupabaseClient } from "@/lib/supabase/client";
import { hasSupabaseAuthConfig } from "@/lib/supabase/config";
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

type ExperimentAccessState = "ready" | "auth_required" | "auth_unavailable";
type BrowserSupabaseClient = ReturnType<typeof createSupabaseClient>;
type ViewerAccessResolution =
  | {
      accessState: "ready";
      viewerUserId: string;
      errorMessage: null;
    }
  | {
      accessState: "auth_required" | "auth_unavailable";
      viewerUserId: null;
      errorMessage: string | null;
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
    attach_recipe_ids?: string[];
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

function resolveViewerUserId(user: User | null | undefined): string | null {
  const normalizedUserId = user?.id?.trim() ?? "";
  return normalizedUserId || null;
}

async function resolveViewerAccessClient(
  supabase: BrowserSupabaseClient,
): Promise<ViewerAccessResolution> {
  try {
    const { data, error } = await supabase.auth.getUser();
    const viewerUserId = resolveViewerUserId(data.user);

    if (viewerUserId) {
      return {
        accessState: "ready",
        viewerUserId,
        errorMessage: null,
      };
    }

    if (error?.message && !isExpectedSignedOutMessage(error.message)) {
      return {
        accessState: "auth_unavailable",
        viewerUserId: null,
        errorMessage: error.message,
      };
    }

    return {
      accessState: "auth_required",
      viewerUserId: null,
      errorMessage: null,
    };
  } catch (error) {
    return {
      accessState: "auth_unavailable",
      viewerUserId: null,
      errorMessage:
        error instanceof Error && error.message
          ? error.message
          : "Failed to verify your account.",
    };
  }
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

function getAccessState(error: unknown): ExperimentAccessState | null {
  if (!(error instanceof BrowserApiError)) {
    return null;
  }
  if (error.status === 401) {
    return "auth_required";
  }
  if (error.status === 503) {
    return "auth_unavailable";
  }
  return null;
}

function getAccessStateCopy(accessState: ExperimentAccessState): {
  badgeLabel: string;
  title: string;
  description: string;
  sidebarTitle: string;
  sidebarDescription: string;
} {
  if (accessState === "auth_required") {
    return {
      badgeLabel: "Private workspace",
      title: "Sign in to open Recipe Lab",
      description:
        "Your experiment threads, recipe attachments, and saved context now stay tied to your account. Sign in to keep brainstorming where you left off.",
      sidebarTitle: "Sign in for history",
      sidebarDescription:
        "Thread history is now private to each account, so the lab stays personal instead of shared.",
    };
  }

  return {
    badgeLabel: "Setup required",
    title: "Recipe Lab needs authentication setup",
    description:
      "Private experiment threads depend on Supabase Auth. Add the auth configuration, then reload to unlock history and messaging.",
    sidebarTitle: "Authentication unavailable",
    sidebarDescription:
      "Recipe Lab history cannot load until authentication is configured for this environment.",
  };
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
    title: thread.title,
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

function renderMessageContent(
  message: ExperimentMessageRecord,
  isStreamingAssistantPlaceholder: boolean,
): ReactNode {
  const content = isStreamingAssistantPlaceholder ? "Working on your recipe..." : message.content;
  if (message.role === "user") {
    return <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>;
  }

  return (
    <div className="text-sm leading-relaxed [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_a]:underline [&_a]:decoration-primary/40 [&_a]:underline-offset-4 [&_a:hover]:decoration-primary [&_blockquote]:my-2 [&_blockquote]:border-l-2 [&_blockquote]:border-border/70 [&_blockquote]:pl-3 [&_code]:rounded [&_code]:bg-muted/60 [&_code]:px-1 [&_h1]:my-2 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:my-2 [&_h2]:text-base [&_h2]:font-semibold [&_h3]:my-2 [&_h3]:text-sm [&_h3]:font-semibold [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_pre]:my-2 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted/40 [&_pre]:p-2 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node, ...props }) => {
            void node;
            return <a {...props} target="_blank" rel="noreferrer noopener" />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default function ExperimentPage() {
  const router = useRouter();
  const hasAuthConfig = hasSupabaseAuthConfig();
  const [supabase] = useState(() => (hasAuthConfig ? createSupabaseClient() : null));
  const [messageInput, setMessageInput] = useState("");
  const [thread, setThread] = useState<ExperimentThreadRecord | null>(null);
  const [threadHistory, setThreadHistory] = useState<ExperimentThreadSummary[]>([]);
  const [isCreatingThread, setIsCreatingThread] = useState(false);
  const [isLoadingThread, setIsLoadingThread] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [accessState, setAccessState] = useState<ExperimentAccessState>(
    hasAuthConfig ? "ready" : "auth_unavailable",
  );
  const [viewerUserId, setViewerUserId] = useState<string | null>(null);
  const [isResolvingViewer, setIsResolvingViewer] = useState(hasAuthConfig);
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
  const messageListEndRef = useRef<HTMLDivElement | null>(null);
  const viewerUserIdRef = useRef<string | null>(null);
  const activeThreadId = thread?.id ?? null;
  const activeThreadMessageCount = thread?.messages.length ?? 0;
  const isAccessPending = isResolvingViewer;
  const isAccessBlocked = !isAccessPending && accessState !== "ready";
  const canUseThreads = !isAccessPending && accessState === "ready";
  const accessStateCopy = isAccessBlocked ? getAccessStateCopy(accessState) : null;
  const canSendMessage =
    canUseThreads &&
    !isSendingMessage &&
    messageInput.trim().length > 0 &&
    !isCreatingThread &&
    !isLoadingThread;

  function resetExperimentState() {
    setIsCreatingThread(false);
    setIsLoadingThread(false);
    setIsLoadingHistory(false);
    setIsSendingMessage(false);
    setThread(null);
    setThreadHistory([]);
    setMessageInput("");
    setPendingAttachments([]);
    setIsAttachDialogOpen(false);
    setAttachSearchInput("");
    setAttachSearchResults([]);
    setIsSearchingAttachments(false);
    setAttachSearchError(null);
    setAttachmentFeedback(null);
    setStreamStatus(null);
    setStreamingMessageId(null);
    setErrorMessage(null);
  }

  function applyAccessState(nextAccessState: ExperimentAccessState) {
    setAccessState(nextAccessState);
    resetExperimentState();
  }

  function applyBlockingAccessState(nextAccessState: ExperimentAccessState) {
    if (nextAccessState === "auth_required") {
      viewerUserIdRef.current = null;
      setViewerUserId(null);
    }
    applyAccessState(nextAccessState);
  }

  function applyViewerAccessResolution(resolution: ViewerAccessResolution) {
    if (resolution.accessState === "ready") {
      if (viewerUserIdRef.current === resolution.viewerUserId && accessState === "ready") {
        setErrorMessage(null);
        return;
      }
      viewerUserIdRef.current = resolution.viewerUserId;
      setViewerUserId(resolution.viewerUserId);
      setAccessState("ready");
      resetExperimentState();
      setIsLoadingHistory(true);
      return;
    }

    viewerUserIdRef.current = null;
    setViewerUserId(null);
    applyBlockingAccessState(resolution.accessState);
    if (resolution.errorMessage) {
      setErrorMessage(resolution.errorMessage);
    }
  }

  function isViewerStillActive(activeViewerUserId: string | null): boolean {
    return Boolean(activeViewerUserId && viewerUserIdRef.current === activeViewerUserId);
  }

  const applyBlockingAccessStateFromEffect = useEffectEvent(
    (nextAccessState: ExperimentAccessState) => {
      applyBlockingAccessState(nextAccessState);
    },
  );

  const applyViewerAccessResolutionFromEffect = useEffectEvent(
    (resolution: ViewerAccessResolution) => {
      applyViewerAccessResolution(resolution);
    },
  );

  async function refreshHistory(activeViewerUserId: string | null = viewerUserIdRef.current) {
    if (!activeViewerUserId) {
      setIsLoadingHistory(false);
      return;
    }

    setIsLoadingHistory(true);
    try {
      const response = await listThreadsClient(40);
      if (viewerUserIdRef.current !== activeViewerUserId) {
        return;
      }
      setAccessState("ready");
      setThreadHistory(response.threads ?? []);
    } catch (error) {
      if (viewerUserIdRef.current !== activeViewerUserId) {
        return;
      }
      const nextAccessState = getAccessState(error);
      if (nextAccessState) {
        applyBlockingAccessState(nextAccessState);
        return;
      }
      setThreadHistory([]);
    } finally {
      if (viewerUserIdRef.current === activeViewerUserId) {
        setIsLoadingHistory(false);
      }
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
    if (!supabase) {
      applyBlockingAccessStateFromEffect("auth_unavailable");
      setIsResolvingViewer(false);
      return;
    }

    let isActive = true;
    setIsResolvingViewer(true);

    void resolveViewerAccessClient(supabase)
      .then((resolution) => {
        if (!isActive) {
          return;
        }
        applyViewerAccessResolutionFromEffect(resolution);
      })
      .finally(() => {
        if (isActive) {
          setIsResolvingViewer(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, [supabase]);

  const handleAuthStateChangeFromEffect = useEffectEvent((nextViewerUser: User | null) => {
    const nextViewerUserId = resolveViewerUserId(nextViewerUser);
    if (!nextViewerUserId) {
      setIsResolvingViewer(false);
      applyBlockingAccessState("auth_required");
      return;
    }
    if (viewerUserIdRef.current === nextViewerUserId && accessState === "ready") {
      setIsResolvingViewer(false);
      setErrorMessage(null);
      return;
    }

    setIsResolvingViewer(false);
    applyViewerAccessResolution({
      accessState: "ready",
      viewerUserId: nextViewerUserId,
      errorMessage: null,
    });
  });

  useEffect(() => {
    if (!supabase) {
      return;
    }

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      handleAuthStateChangeFromEffect(session?.user ?? null);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [supabase]);

  const loadViewerHistory = useEffectEvent((activeViewerUserId: string) => {
    void refreshHistory(activeViewerUserId);
  });

  useEffect(() => {
    if (!viewerUserId) {
      return;
    }
    loadViewerHistory(viewerUserId);
  }, [viewerUserId]);

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

  useEffect(() => {
    if (!activeThreadMessageCount) {
      return;
    }
    const messageListEnd = messageListEndRef.current;
    if (!messageListEnd || typeof messageListEnd.scrollIntoView !== "function") {
      return;
    }
    messageListEnd.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [activeThreadId, activeThreadMessageCount]);

  async function handleNewThread() {
    if (!canUseThreads) {
      return;
    }
    const activeViewerUserId = viewerUserIdRef.current;
    if (!activeViewerUserId) {
      return;
    }
    setErrorMessage(null);
    setAttachmentFeedback(null);
    setStreamStatus(null);
    setStreamingMessageId(null);
    setPendingAttachments([]);
    setIsCreatingThread(true);

    try {
      const response = await createThreadClient();
      if (!isViewerStillActive(activeViewerUserId)) {
        return;
      }
      setAccessState("ready");
      const nextThread = normalizeThread(response.thread);
      setThread(nextThread);
      await refreshHistory(activeViewerUserId);
    } catch (error) {
      if (!isViewerStillActive(activeViewerUserId)) {
        return;
      }
      const nextAccessState = getAccessState(error);
      if (nextAccessState) {
        applyBlockingAccessState(nextAccessState);
        return;
      }
      setErrorMessage(getErrorMessage(error, "Failed to start a new conversation."));
    } finally {
      if (isViewerStillActive(activeViewerUserId)) {
        setIsCreatingThread(false);
      }
    }
  }

  async function handleSelectThread(threadId: string) {
    if (!canUseThreads) {
      return;
    }
    const activeViewerUserId = viewerUserIdRef.current;
    if (!activeViewerUserId) {
      return;
    }
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
      if (!isViewerStillActive(activeViewerUserId)) {
        return;
      }
      setAccessState("ready");
      const nextThread = normalizeThread(response.thread);
      setThread(nextThread);
    } catch (error) {
      if (!isViewerStillActive(activeViewerUserId)) {
        return;
      }
      const nextAccessState = getAccessState(error);
      if (nextAccessState) {
        applyBlockingAccessState(nextAccessState);
        return;
      }
      setErrorMessage(getErrorMessage(error, "Failed to load conversation."));
    } finally {
      if (isViewerStillActive(activeViewerUserId)) {
        setIsLoadingThread(false);
      }
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
    if (!canUseThreads) {
      return;
    }
    setMessageInput(prompt);
    if (!thread && !isCreatingThread && !isLoadingThread) {
      void handleNewThread();
    }
  }

  async function handleSendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canUseThreads) {
      return;
    }
    const activeViewerUserId = viewerUserIdRef.current;
    if (!activeViewerUserId) {
      return;
    }
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
        if (!isViewerStillActive(activeViewerUserId)) {
          return;
        }
        setAccessState("ready");
        activeThread = normalizeThread(createResponse.thread);
        setThread(activeThread);
        upsertThreadHistory(activeThread);
        void refreshHistory(activeViewerUserId);
      } catch (error) {
        if (!isViewerStillActive(activeViewerUserId)) {
          return;
        }
        const nextAccessState = getAccessState(error);
        if (nextAccessState) {
          applyBlockingAccessState(nextAccessState);
          setIsSendingMessage(false);
          setStreamStatus(null);
          setStreamingMessageId(null);
          return;
        }
        setErrorMessage(getErrorMessage(error, "Failed to start a new conversation."));
        setIsSendingMessage(false);
        setStreamStatus(null);
        setStreamingMessageId(null);
        return;
      } finally {
        if (isViewerStillActive(activeViewerUserId)) {
          setIsCreatingThread(false);
        }
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

    try {
      const response = await streamMessageClient(activeThread.id, {
        content: normalizedMessage,
        ...(pendingAttachments.length
          ? { attach_recipe_ids: pendingAttachments.map((item) => item.id) }
          : {}),
      });

      if (!response.body) {
        throw new BrowserApiError("Streaming response body was empty.", 500);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      const streamState: {
        finalPayload: CreateExperimentMessageResponse | null;
        streamError: string | null;
        receivedDelta: boolean;
        assistantText: string;
      } = {
        finalPayload: null,
        streamError: null,
        receivedDelta: false,
        assistantText: "",
      };

      const applyStreamEvent = (parsed: ParsedSseEvent) => {
        if (!isViewerStillActive(activeViewerUserId)) {
          return;
        }
        if (parsed.event === "status") {
          const data = parsed.data as { step?: string };
          if (data?.step) {
            setStreamStatus(data.step === "drafting" ? "Drafting response..." : data.step);
          }
          return;
        }

        if (parsed.event === "delta") {
          const data = parsed.data as { text?: string } | string;
          const deltaText =
            typeof data === "string" ? data : typeof data?.text === "string" ? data.text : null;
          if (deltaText) {
            streamState.receivedDelta = true;
            streamState.assistantText += deltaText;
            setThread((currentThread) => {
              if (!currentThread || currentThread.id !== activeThread.id) {
                return currentThread;
              }
              return {
                ...currentThread,
                messages: currentThread.messages.map((message) =>
                  message.id === optimisticAssistantMessageId
                    ? { ...message, content: `${message.content}${deltaText}` }
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
          streamState.finalPayload = parsed.data as CreateExperimentMessageResponse;
          return;
        }

        if (parsed.event === "error") {
          const data = parsed.data as { detail?: string };
          streamState.streamError = data?.detail ?? "Failed to stream assistant response.";
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

      if (!isViewerStillActive(activeViewerUserId)) {
        return;
      }

      if (streamState.streamError) {
        throw new BrowserApiError(streamState.streamError, 500, streamState.streamError);
      }
      if (!streamState.finalPayload && !streamState.receivedDelta) {
        throw new BrowserApiError("Stream ended without assistant content.", 500);
      }

      let nextThreadSummary: ExperimentThreadRecord;
      if (streamState.finalPayload) {
        const finalThread = normalizeThread(streamState.finalPayload.thread);
        const finalUserMessage = streamState.finalPayload.user_message;
        const finalAssistantMessage = streamState.finalPayload.assistant_message;
        const finalAttachmentMessage = streamState.finalPayload.attachment_message;
        setThread((currentThread) => {
          if (!currentThread || currentThread.id !== finalThread.id) {
            return currentThread;
          }
          const mergedMessages = currentThread.messages
            .map((message) => {
              if (message.id === optimisticUserMessage.id) {
                return finalUserMessage;
              }
              if (message.id === optimisticAssistantMessageId) {
                return {
                  ...finalAssistantMessage,
                  content: message.content || finalAssistantMessage.content,
                };
              }
              return message;
            })
            .concat(
              finalAttachmentMessage &&
                !currentThread.messages.some(
                  (message) => message.id === finalAttachmentMessage.id,
                )
                ? [finalAttachmentMessage]
                : [],
            )
            .sort((left, right) => left.sequence_no - right.sequence_no);
          return {
            ...currentThread,
            mode: finalThread.mode,
            title: finalThread.title,
            metadata: finalThread.metadata,
            created_at: finalThread.created_at,
            updated_at: finalThread.updated_at,
            context_recipe_ids: finalThread.context_recipe_ids,
            messages: mergedMessages,
          };
        });
        nextThreadSummary = finalThread;
      } else {
        nextThreadSummary = {
          ...activeThread,
          title: activeThread.title ?? normalizedMessage.slice(0, 80),
          messages: [
            ...activeThread.messages,
            optimisticUserMessage,
            {
              ...optimisticAssistantMessage,
              content: streamState.assistantText || optimisticAssistantMessage.content,
            },
          ],
        };
      }
      setMessageInput("");
      setPendingAttachments([]);
      setAttachSearchInput("");
      setAttachSearchResults([]);
      setIsAttachDialogOpen(false);

      if (streamState.finalPayload) {
        const finalAttachmentText = attachmentFeedbackText(streamState.finalPayload);
        if (finalAttachmentText) {
          setAttachmentFeedback(finalAttachmentText);
        }
      }
      upsertThreadHistory(nextThreadSummary);
    } catch (error) {
      if (!isViewerStillActive(activeViewerUserId)) {
        return;
      }
      const nextAccessState = getAccessState(error);
      if (nextAccessState) {
        applyBlockingAccessState(nextAccessState);
        return;
      }
      setThread(previousThreadSnapshot);
      setErrorMessage(getErrorMessage(error, "Failed to send message."));
    } finally {
      if (isViewerStillActive(activeViewerUserId)) {
        setIsSendingMessage(false);
        setStreamStatus(null);
        setStreamingMessageId(null);
      }
    }
  }

  async function handleAccessRetry() {
    if (isAccessPending) {
      return;
    }
    if (!supabase) {
      applyBlockingAccessState("auth_unavailable");
      return;
    }
    if (viewerUserIdRef.current) {
      await refreshHistory(viewerUserIdRef.current);
      return;
    }
    setIsResolvingViewer(true);
    try {
      applyViewerAccessResolution(await resolveViewerAccessClient(supabase));
    } finally {
      setIsResolvingViewer(false);
    }
  }

  const isBusy = isCreatingThread || isLoadingThread || isSendingMessage || isAccessPending;
  const normalizedAttachQuery = attachSearchInput.trim();
  const latestAssistantMessage =
    [...(thread?.messages ?? [])]
      .reverse()
      .find((message) => message.role === "assistant" && message.content.trim().length > 0) ??
    null;

  function handleOpenAddRecipeFlow() {
    if (isBusy) {
      return;
    }
    if (!latestAssistantMessage || !saveExperimentRecipeDraft(latestAssistantMessage.content)) {
      setErrorMessage("Unable to transfer the latest assistant draft to Add Recipe.");
      return;
    }
    setErrorMessage(null);
    router.push("/recipes/new");
  }

  return (
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto w-full max-w-[1500px] space-y-6 px-4 py-8 sm:px-6 sm:py-10">
        <section className="space-y-2">
          <Badge className="rounded-full px-3 py-0.5">Experiment</Badge>
          <h1 className="font-display text-4xl leading-tight sm:text-5xl">
            Recipe Lab
          </h1>
          <p className="max-w-3xl text-base text-muted-foreground">
            Build new ideas or modify existing recipes in one continuous, attach-aware chat thread.
          </p>
        </section>

        <section className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)] xl:grid-cols-[260px_minmax(0,1fr)]">
          <Card className="h-[82vh]">
            <CardHeader className="space-y-3">
              <CardTitle className="flex items-center gap-2 text-xl">
                <History className="size-4 text-primary" />
                {isAccessPending || isAccessBlocked ? "Private history" : "History"}
              </CardTitle>
              {canUseThreads ? (
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
              ) : null}
            </CardHeader>
            <CardContent className="h-[calc(82vh-8rem)] space-y-2 overflow-y-auto">
              {isAccessPending ? (
                <div className="flex h-full flex-col justify-center gap-3 rounded-xl border border-dashed border-border/80 bg-muted/20 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold">
                    <Loader2 className="size-4 animate-spin text-primary" />
                    Checking your account
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Recipe Lab waits for your account before requesting private thread history.
                  </p>
                </div>
              ) : isAccessBlocked && accessStateCopy ? (
                <div className="flex h-full flex-col justify-center gap-3 rounded-xl border border-dashed border-border/80 bg-muted/20 p-4">
                  <p className="text-sm font-semibold">{accessStateCopy.sidebarTitle}</p>
                  <p className="text-sm text-muted-foreground">
                    {accessStateCopy.sidebarDescription}
                  </p>
                </div>
              ) : isLoadingHistory ? (
                <p className="text-sm text-muted-foreground">Loading…</p>
              ) : threadHistory.length === 0 ? (
                <p className="text-sm text-muted-foreground">No conversation history yet.</p>
              ) : (
                threadHistory.map((threadItem) => (
                  <Button
                    key={threadItem.id}
                    type="button"
                    variant="ghost"
                    className={`h-auto w-full justify-start rounded-md border px-3 py-2 text-left transition-colors ${
                      thread?.id === threadItem.id
                        ? "border-primary/40 bg-primary/5"
                        : "border-border/70 hover:bg-accent/40"
                    }`}
                    onClick={() => void handleSelectThread(threadItem.id)}
                  >
                    <span className="w-full">
                      <p className="truncate text-sm font-medium">{formatThreadLabel(threadItem)}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {formatHistoryPreview(threadItem)}
                      </p>
                    </span>
                  </Button>
                ))
              )}
            </CardContent>
          </Card>

          <Card className="h-[82vh] overflow-hidden">
            <CardHeader>
              <CardTitle>
                {isAccessPending
                  ? "Checking your Recipe Lab access"
                  : isAccessBlocked && accessStateCopy
                  ? accessStateCopy.title
                  : thread
                  ? thread.title?.trim() || "Untitled conversation"
                  : "Start a new conversation"}
              </CardTitle>
              <CardDescription>
                {isAccessPending
                  ? "Loading your account state before requesting private thread history."
                  : isAccessBlocked && accessStateCopy
                  ? accessStateCopy.description
                  : thread
                  ? "Continue the thread or attach recipes before your next message."
                  : "Type a message to start instantly, or use New Thread."}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex h-[calc(82vh-7.5rem)] min-h-0 flex-col gap-4">
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
                {isAccessPending ? (
                  <div className="flex h-full items-center justify-center overflow-y-auto p-4 sm:p-6">
                    <div className="w-full max-w-xl rounded-[1.75rem] border border-border/70 bg-background/90 p-5 shadow-sm sm:p-6">
                      <div className="flex items-start gap-4">
                        <span className="inline-flex size-11 items-center justify-center rounded-2xl bg-primary/12 text-primary">
                          <Loader2 className="size-5 animate-spin" />
                        </span>
                        <div className="space-y-2">
                          <p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
                            Loading access
                          </p>
                          <h2 className="font-display text-3xl leading-tight tracking-tight sm:text-4xl">
                            Checking your Recipe Lab access
                          </h2>
                          <p className="max-w-[56ch] text-sm leading-relaxed text-muted-foreground sm:text-base">
                            Thread history stays hidden until the current account is resolved, so
                            signed-out visitors do not trigger private history requests.
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : isAccessBlocked && accessStateCopy ? (
                  <div className="flex h-full items-center justify-center overflow-y-auto p-4 sm:p-6">
                    <div className="w-full max-w-2xl rounded-[1.75rem] border border-border/70 bg-background/90 p-5 shadow-sm sm:p-6">
                      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-4">
                          <span className="inline-flex size-11 items-center justify-center rounded-2xl bg-primary/12 text-primary">
                            <LockKeyhole className="size-5" />
                          </span>
                          <div className="space-y-2">
                            <p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
                              {accessStateCopy.badgeLabel}
                            </p>
                            <h2 className="font-display text-3xl leading-tight tracking-tight sm:text-4xl">
                              {accessStateCopy.title}
                            </h2>
                            <p className="max-w-[56ch] text-sm leading-relaxed text-muted-foreground sm:text-base">
                              {accessStateCopy.description}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <Badge variant="secondary" className="rounded-full px-3 py-1">
                              Private history
                            </Badge>
                            <Badge variant="secondary" className="rounded-full px-3 py-1">
                              Saved recipe context
                            </Badge>
                            <Badge variant="secondary" className="rounded-full px-3 py-1">
                              Account-scoped drafts
                            </Badge>
                          </div>
                        </div>

                        <div className="flex shrink-0 flex-col items-start gap-3 lg:items-end">
                          {accessState === "auth_required" ? (
                            <>
                              <AuthProfileButton />
                              <p className="max-w-xs text-sm text-muted-foreground lg:text-right">
                                Sign in here or from the header to continue in your personal lab.
                              </p>
                            </>
                          ) : (
                            <>
                              <Button
                                type="button"
                                variant="outline"
                                onClick={() => {
                                  void handleAccessRetry();
                                }}
                              >
                                Check again
                              </Button>
                              <p className="max-w-xs text-sm text-muted-foreground lg:text-right">
                                Once authentication is configured, reload this view to restore
                                thread history and messaging.
                              </p>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : !thread ? (
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
                          <Button
                            key={prompt}
                            type="button"
                            variant="outline"
                            className="h-auto justify-start whitespace-normal border-border/70 bg-background px-3 py-2 text-left text-sm hover:bg-accent/40"
                            onClick={() => applyStarterPrompt(prompt)}
                            disabled={isBusy}
                          >
                            {prompt}
                          </Button>
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
                          <Button
                            key={prompt}
                            type="button"
                            variant="outline"
                            className="h-auto justify-start whitespace-normal border-border/70 bg-background px-3 py-2 text-left text-sm hover:bg-accent/40"
                            onClick={() => applyStarterPrompt(prompt)}
                            disabled={isBusy}
                          >
                            {prompt}
                          </Button>
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
                        {renderMessageContent(
                          message,
                          isSendingMessage &&
                            streamingMessageId === message.id &&
                            !message.content.trim(),
                        )}
                      </article>
                    ))}
                    <div ref={messageListEndRef} aria-hidden="true" />
                  </div>
                )}
              </div>

              {!isAccessBlocked ? (
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
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon-xs"
                              className="opacity-80 transition-opacity hover:opacity-100"
                              onClick={() => removePendingAttachment(attachment.id)}
                              aria-label={`Remove ${attachment.name}`}
                            >
                              <X className="size-3" />
                            </Button>
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
                                      <p className="truncate text-sm font-medium">
                                        {result.name}
                                      </p>
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
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="icon-xs"
                                      className="opacity-80 transition-opacity hover:opacity-100"
                                      onClick={() => removePendingAttachment(attachment.id)}
                                      aria-label={`Remove ${attachment.name}`}
                                    >
                                      <X className="size-3" />
                                    </Button>
                                  </Badge>
                                ))}
                              </div>
                            ) : (
                              <p className="text-sm text-muted-foreground">
                                No recipes attached yet.
                              </p>
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

                    <div className="flex items-center gap-2">
                      {latestAssistantMessage ? (
                        <Button
                          type="button"
                          variant="secondary"
                          disabled={isBusy}
                          onClick={handleOpenAddRecipeFlow}
                        >
                          <Sparkles className="size-4" />
                          Add As Recipe
                        </Button>
                      ) : null}

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
                  </div>
                </form>
              ) : null}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
