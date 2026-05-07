import Link from "next/link";
import { Plus, Search, TriangleAlert } from "lucide-react";

import { ForkfolioHeader } from "@/components/forkfolio-header";
import { PageBackLink, PageHero, PageMain, PageShell } from "@/components/page-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function RecipeNotFoundPage() {
  return (
    <PageShell>
      <ForkfolioHeader />

      <PageMain className="max-w-3xl space-y-6 ff-animate-enter">
        <PageBackLink href="/browse" label="Back to Browse" />

        <PageHero
          badge="Recipe Not Found"
          title="This recipe no longer exists."
          description="It may have been deleted, moved, or the link may be incorrect."
          contentClassName="max-w-3xl"
        >
          <Card className="border-border/80 bg-background/82 shadow-none">
            <CardHeader className="space-y-3">
              <Badge variant="secondary" className="w-fit rounded-full px-3 py-0.5 text-xs">
                <TriangleAlert className="size-3.5" />
                Missing Recipe Link
              </Badge>
              <CardTitle className="font-display text-3xl tracking-tight">
                Try another path
              </CardTitle>
              <CardDescription>
                Browse your saved recipes or import a new one from text or URL.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3 sm:flex-row">
              <Button asChild className="sm:flex-1">
                <Link href="/browse">
                  <Search className="size-4" />
                  Browse Recipes
                </Link>
              </Button>
              <Button asChild variant="outline" className="sm:flex-1">
                <Link href="/recipes/new">
                  <Plus className="size-4" />
                  Add Recipe
                </Link>
              </Button>
            </CardContent>
          </Card>
        </PageHero>
      </PageMain>
    </PageShell>
  );
}
