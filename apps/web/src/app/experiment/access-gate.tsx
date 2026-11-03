"use client";

import { Loader2, LockKeyhole } from "lucide-react";

import { AuthProfileButton } from "@/components/auth-profile-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export type BlockedAccessReason = "auth_required" | "auth_unavailable";

type Copy = {
  badgeLabel: string;
  title: string;
  description: string;
  sidebarTitle: string;
  sidebarDescription: string;
};

const RESOLVING_COPY = {
  sidebarTitle: "Checking your account",
  sidebarDescription:
    "Recipe Lab waits for your account before requesting private thread history.",
  title: "Checking your Recipe Lab access",
  description: "Loading your account state before requesting private thread history.",
  panelTagline: "Loading access",
  panelBody:
    "Thread history stays hidden until the current account is resolved, so signed-out visitors do not trigger private history requests.",
};

const BLOCKED_COPY: Record<BlockedAccessReason, Copy> = {
  auth_required: {
    badgeLabel: "Private workspace",
    title: "Sign in to open Recipe Lab",
    description:
      "Your experiment threads, recipe attachments, and saved context now stay tied to your account. Sign in to keep brainstorming where you left off.",
    sidebarTitle: "Sign in for history",
    sidebarDescription:
      "Thread history is now private to each account, so the lab stays personal instead of shared.",
  },
  auth_unavailable: {
    badgeLabel: "Setup required",
    title: "Recipe Lab needs authentication setup",
    description:
      "Private experiment threads depend on Supabase Auth. Add the auth configuration, then reload to unlock history and messaging.",
    sidebarTitle: "Authentication unavailable",
    sidebarDescription:
      "Recipe Lab history cannot load until authentication is configured for this environment.",
  },
};

export function getBlockedAccessCopy(reason: BlockedAccessReason): Copy {
  return BLOCKED_COPY[reason];
}

export function AccessSidebar({
  variant,
  reason,
}: {
  variant: "resolving" | "blocked";
  reason?: BlockedAccessReason;
}) {
  if (variant === "resolving") {
    return (
      <div className="flex h-full flex-col justify-center gap-3 rounded-xl border border-dashed border-border/80 bg-muted/20 p-4">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Loader2 className="size-4 animate-spin text-primary" />
          {RESOLVING_COPY.sidebarTitle}
        </div>
        <p className="text-sm text-muted-foreground">{RESOLVING_COPY.sidebarDescription}</p>
      </div>
    );
  }
  const copy = BLOCKED_COPY[reason!];
  return (
    <div className="flex h-full flex-col justify-center gap-3 rounded-xl border border-dashed border-border/80 bg-muted/20 p-4">
      <p className="text-sm font-semibold">{copy.sidebarTitle}</p>
      <p className="text-sm text-muted-foreground">{copy.sidebarDescription}</p>
    </div>
  );
}

export function AccessPanel({
  variant,
  reason,
  onRetry,
}: {
  variant: "resolving" | "blocked";
  reason?: BlockedAccessReason;
  onRetry?: () => void;
}) {
  if (variant === "resolving") {
    return (
      <div className="flex h-full items-center justify-center overflow-y-auto p-4 sm:p-6">
        <div className="w-full max-w-xl rounded-[1.75rem] border border-border/70 bg-background/90 p-5 shadow-sm sm:p-6">
          <div className="flex items-start gap-4">
            <span className="inline-flex size-11 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <Loader2 className="size-5 animate-spin" />
            </span>
            <div className="space-y-2">
              <p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
                {RESOLVING_COPY.panelTagline}
              </p>
              <h2 className="font-display text-3xl leading-tight tracking-tight sm:text-4xl">
                {RESOLVING_COPY.title}
              </h2>
              <p className="max-w-[56ch] text-sm leading-relaxed text-muted-foreground sm:text-base">
                {RESOLVING_COPY.panelBody}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }
  const copy = BLOCKED_COPY[reason!];
  return (
    <div className="flex h-full items-center justify-center overflow-y-auto p-4 sm:p-6">
      <div className="w-full max-w-2xl rounded-[1.75rem] border border-border/70 bg-background/90 p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-4">
            <span className="inline-flex size-11 items-center justify-center rounded-2xl bg-primary/12 text-primary">
              <LockKeyhole className="size-5" />
            </span>
            <div className="space-y-2">
              <p className="text-xs font-semibold tracking-[0.16em] text-muted-foreground uppercase">
                {copy.badgeLabel}
              </p>
              <h2 className="font-display text-3xl leading-tight tracking-tight sm:text-4xl">
                {copy.title}
              </h2>
              <p className="max-w-[56ch] text-sm leading-relaxed text-muted-foreground sm:text-base">
                {copy.description}
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
            {reason === "auth_required" ? (
              <>
                <AuthProfileButton />
                <p className="max-w-xs text-sm text-muted-foreground lg:text-right">
                  Sign in here or from the header to continue in your personal lab.
                </p>
              </>
            ) : (
              <>
                <Button type="button" variant="outline" onClick={onRetry}>
                  Check again
                </Button>
                <p className="max-w-xs text-sm text-muted-foreground lg:text-right">
                  Once authentication is configured, reload this view to restore thread history and
                  messaging.
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
