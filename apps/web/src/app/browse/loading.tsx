import { ForkfolioHeader } from "@/components/forkfolio-header";
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
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <section className="rounded-[2rem] border border-border/70 bg-card/35 px-6 py-10 sm:px-10">
          <div className="mx-auto max-w-4xl space-y-6">
            <div className="space-y-3">
              <Skeleton className="h-5 w-28 rounded-full" />
              <Skeleton className="h-14 w-2/3" />
              <Skeleton className="h-6 w-4/5" />
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Skeleton className="h-14 flex-1 rounded-2xl" />
              <Skeleton className="h-14 w-full rounded-2xl sm:w-36" />
            </div>
          </div>
        </section>

        <section className="mt-10 space-y-5">
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
      </main>
    </div>
  );
}
