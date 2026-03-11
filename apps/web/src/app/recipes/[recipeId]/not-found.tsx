import Link from "next/link";
import { ArrowLeft, Plus, Search, TriangleAlert } from "lucide-react";

import { ForkfolioHeader } from "@/components/forkfolio-header";
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
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6">
        <Button asChild variant="ghost" className="mb-4">
          <Link href="/browse">
            <ArrowLeft className="size-4" />
            Back to Browse
          </Link>
        </Button>

        <Card className="border-border/80 bg-background/80">
          <CardHeader className="space-y-4">
            <Badge variant="secondary" className="w-fit rounded-full px-3 py-0.5 text-xs">
              <TriangleAlert className="size-3.5" />
              Recipe Not Found
            </Badge>
            <CardTitle className="font-display text-4xl leading-tight tracking-tight text-primary">
              This recipe no longer exists.
            </CardTitle>
            <CardDescription className="text-base">
              It may have been deleted, moved, or the link may be incorrect.
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
      </main>
    </div>
  );
}
