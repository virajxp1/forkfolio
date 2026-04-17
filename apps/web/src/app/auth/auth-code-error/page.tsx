import Link from "next/link";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { PageHero, PageMain, PageShell } from "@/components/page-shell";
import { Button } from "@/components/ui/button";

export default function AuthCodeErrorPage() {
  return (
    <PageShell className="bg-[radial-gradient(circle_at_top,oklch(0.95_0.03_95),transparent_44%),linear-gradient(180deg,color-mix(in_oklab,var(--background)_94%,white),var(--background))]">
      <ForkfolioHeader />
      <PageMain className="pb-16">
        <PageHero
          badge="Auth"
          title="Google sign-in could not be completed"
          description="Check that Supabase Auth is configured with your Google provider callback URL, then try signing in again."
          actions={(
            <Button asChild size="lg" className="rounded-full px-6">
              <Link href="/">Back to home</Link>
            </Button>
          )}
        />
      </PageMain>
    </PageShell>
  );
}
