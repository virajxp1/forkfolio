import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type PageShellProps = {
  children: ReactNode;
  className?: string;
};

export function PageShell({ children, className }: PageShellProps) {
  return <div className={cn("relative isolate min-h-screen overflow-x-hidden pb-10", className)}>{children}</div>;
}

type PageMainProps = {
  children: ReactNode;
  className?: string;
};

export function PageMain({ children, className }: PageMainProps) {
  return (
    <main className={cn("mx-auto w-full max-w-6xl px-4 pt-8 sm:px-6 sm:pt-10", className)}>
      {children}
    </main>
  );
}

type PageBackLinkProps = {
  href: string;
  label: string;
  className?: string;
};

export function PageBackLink({ href, label, className }: PageBackLinkProps) {
  return (
    <Button
      asChild
      variant="ghost"
      size="sm"
      className={cn(
        "mb-5 h-9 rounded-full px-3.5 text-foreground/85 hover:text-foreground",
        className,
      )}
    >
      <Link href={href}>
        <ArrowLeft className="size-4" />
        {label}
      </Link>
    </Button>
  );
}

type PageHeroProps = {
  badge: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
  contentClassName?: string;
};

export function PageHero({
  badge,
  title,
  description,
  actions,
  children,
  className,
  contentClassName,
}: PageHeroProps) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-[2rem] border border-border/70 bg-card/35 px-6 py-8 shadow-[0_24px_70px_-36px_color-mix(in_oklab,var(--primary)_55%,transparent)] sm:px-10 sm:py-10",
        className,
      )}
    >
      <div className="pointer-events-none absolute -top-12 right-8 h-56 w-56 rounded-full bg-[radial-gradient(circle,color-mix(in_oklab,var(--primary)_22%,transparent)_0%,transparent_70%)]" />
      <div className="pointer-events-none absolute -bottom-16 -left-10 h-64 w-64 rounded-full bg-[radial-gradient(circle,color-mix(in_oklab,var(--accent)_22%,transparent)_0%,transparent_72%)]" />

      <div className={cn("relative z-10 mx-auto max-w-5xl space-y-8", contentClassName)}>
        <div className="space-y-3">
          <Badge
            variant="secondary"
            className="rounded-full border border-border/60 bg-background/70 px-3 py-0.5 text-[0.68rem] font-semibold tracking-[0.08em] uppercase"
          >
            {badge}
          </Badge>
          <h1 className="font-display text-[clamp(2.3rem,6vw,4.2rem)] leading-[0.95] tracking-tight text-foreground">
            {title}
          </h1>
          {description ? (
            <p className="max-w-4xl text-base leading-relaxed text-muted-foreground sm:text-lg">
              {description}
            </p>
          ) : null}
        </div>

        {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}

        {children}
      </div>
    </section>
  );
}
