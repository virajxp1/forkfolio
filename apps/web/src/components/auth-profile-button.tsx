"use client";

import type { User } from "@supabase/supabase-js";
import { LoaderCircle, LogIn, LogOut } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useState, useTransition } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { createClient } from "@/lib/supabase/client";
import { hasSupabaseAuthConfig } from "@/lib/supabase/config";

function resolveDisplayName(user: User): string {
  const fullName = typeof user.user_metadata?.full_name === "string"
    ? user.user_metadata.full_name.trim()
    : "";
  if (fullName) {
    return fullName;
  }

  const name = typeof user.user_metadata?.name === "string"
    ? user.user_metadata.name.trim()
    : "";
  if (name) {
    return name;
  }

  const emailPrefix = user.email?.split("@", 1)[0]?.trim();
  return emailPrefix || "Profile";
}

function resolveInitial(label: string): string {
  return label.slice(0, 1).toUpperCase() || "P";
}

export function AuthProfileButton() {
  const pathname = usePathname() ?? "/";
  const [supabase] = useState(() => (
    hasSupabaseAuthConfig() ? createClient() : null
  ));
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(Boolean(supabase));
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!supabase) {
      return;
    }

    let isActive = true;

    void supabase.auth.getUser().then(({ data, error }) => {
      if (!isActive) {
        return;
      }

      setCurrentUser(data.user ?? null);
      setErrorMessage(error?.message ?? null);
      setIsLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!isActive) {
        return;
      }

      setCurrentUser(session?.user ?? null);
      setIsLoading(false);
      if (!session) {
        setIsDialogOpen(false);
      }
    });

    return () => {
      isActive = false;
      subscription.unsubscribe();
    };
  }, [supabase]);

  if (!supabase) {
    return null;
  }

  async function handleGoogleSignIn() {
    if (!supabase) {
      return;
    }

    setErrorMessage(null);

    const normalizedNext = pathname.startsWith("/") ? pathname : "/";
    const nextSearch = new URLSearchParams({ next: normalizedNext }).toString();
    const redirectTo = `${window.location.origin}/auth/callback?${nextSearch}`;

    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo,
      },
    });

    if (error) {
      setErrorMessage(error.message);
    }
  }

  function handleSignOut() {
    if (!supabase) {
      return;
    }

    setErrorMessage(null);

    startTransition(() => {
      void supabase.auth.signOut().then(({ error }) => {
        if (error) {
          setErrorMessage(error.message);
          return;
        }

        setCurrentUser(null);
        setIsDialogOpen(false);
        window.location.assign(pathname);
      });
    });
  }

  if (isLoading) {
    return (
      <Button
        type="button"
        variant="secondary"
        size="sm"
        disabled
        className="h-9 rounded-full px-3.5 sm:w-auto"
      >
        <LoaderCircle className="size-4 animate-spin" />
        Checking profile
      </Button>
    );
  }

  if (!currentUser) {
    return (
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={() => {
          void handleGoogleSignIn();
        }}
        className="h-9 rounded-full px-3.5 shadow-[0_10px_24px_-20px_color-mix(in_oklab,var(--primary)_80%,transparent)] transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-px hover:shadow-[0_14px_30px_-20px_color-mix(in_oklab,var(--primary)_90%,transparent)] sm:w-auto"
      >
        <LogIn className="size-4" />
        Sign In
      </Button>
    );
  }

  const displayName = resolveDisplayName(currentUser);
  const email = currentUser.email?.trim() || "Signed in with Google";
  const profileInitial = resolveInitial(displayName);

  return (
    <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
      <DialogTrigger asChild>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="h-9 justify-start rounded-full px-2.5 shadow-[0_10px_24px_-20px_color-mix(in_oklab,var(--primary)_80%,transparent)] transition-[transform,box-shadow] duration-200 ease-out hover:-translate-y-px hover:shadow-[0_14px_30px_-20px_color-mix(in_oklab,var(--primary)_90%,transparent)] sm:w-auto"
        >
          <span className="inline-flex size-6 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
            {profileInitial}
          </span>
          <span className="max-w-28 truncate">{displayName}</span>
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-sm rounded-[1.5rem] border-border/80 bg-background/95 p-0 shadow-2xl">
        <div className="relative overflow-hidden rounded-t-[1.5rem] border-b border-border/70 bg-[linear-gradient(135deg,color-mix(in_oklab,var(--primary)_16%,transparent),transparent_58%),linear-gradient(180deg,color-mix(in_oklab,var(--accent)_14%,transparent),transparent_100%)] px-6 py-5">
          <div className="flex items-start gap-4">
            <div className="inline-flex size-14 items-center justify-center rounded-2xl bg-background/85 font-display text-2xl font-semibold text-primary shadow-sm">
              {profileInitial}
            </div>
            <DialogHeader className="space-y-1 text-left">
              <DialogTitle className="font-display text-2xl tracking-tight">
                {displayName}
              </DialogTitle>
              <DialogDescription className="truncate text-sm text-muted-foreground">
                {email}
              </DialogDescription>
            </DialogHeader>
          </div>
        </div>

        <div className="space-y-5 px-6 py-5">
          <div className="rounded-2xl border border-border/70 bg-card/60 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge
                variant="secondary"
                className="rounded-full border border-border/60 bg-background/80 px-3 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] uppercase"
              >
                Google Account
              </Badge>
              {currentUser.email_confirmed_at ? (
                <Badge
                  variant="secondary"
                  className="rounded-full bg-primary/10 px-3 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] uppercase text-primary"
                >
                  Verified
                </Badge>
              ) : null}
            </div>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Signed in as <span className="font-medium text-foreground">{email}</span>.
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              This account is ready for profile-based recipe ownership and saved collections.
            </p>
          </div>

          {errorMessage ? (
            <p className="rounded-xl border border-destructive/20 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {errorMessage}
            </p>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="secondary"
              onClick={handleSignOut}
              disabled={isPending}
              className="rounded-full"
            >
              {isPending ? (
                <LoaderCircle className="size-4 animate-spin" />
              ) : (
                <LogOut className="size-4" />
              )}
              Sign Out
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
