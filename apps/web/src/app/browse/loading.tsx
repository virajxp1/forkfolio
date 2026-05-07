import { ForkfolioHeader } from "@/components/forkfolio-header";
import { PageHero, PageMain, PageShell } from "@/components/page-shell";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function ResultCardSkeleton() {
  return (
    <Card className="h-full border-border/80">
      <CardHeader className="space-y-4">
        <Skeleton className="h-8 w-2/3 rounded-lg" />
        <div className="flex gap-2">
          <Skeleton className="h-6 w-24 rounded-full" />
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-3 w-16 rounded" />
        <Skeleton className="h-4 w-11/12" />
        <Skeleton className="h-4 w-10/12" />
        <Skeleton className="h-4 w-9/12" />
        <Skeleton className="mt-2 h-4 w-28" />
      </CardContent>
    </Card>
  );
}

export default function BrowseLoading() {
  return (
    <PageShell>
      <ForkfolioHeader />

      <PageMain className="space-y-10">
        <PageHero
          badge="Browse Recipes"
          title="Find anything instantly"
          description="Browse your latest recipes or search by dish, ingredient, or cuisine."
          contentClassName="max-w-4xl"
        >
          <div className="space-y-3">
            <Skeleton className="h-14 w-2/3" />
            <Skeleton className="h-6 w-4/5" />
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Skeleton className="h-14 flex-1 rounded-2xl" />
            <Skeleton className="h-14 w-full rounded-2xl sm:w-36" />
          </div>
        </PageHero>

        <section className="space-y-5">
          <Skeleton className="h-10 w-64" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            <ResultCardSkeleton />
            <ResultCardSkeleton />
            <ResultCardSkeleton />
            <ResultCardSkeleton />
            <ResultCardSkeleton />
            <ResultCardSkeleton />
          </div>
        </section>
      </PageMain>
    </PageShell>
  );
}
