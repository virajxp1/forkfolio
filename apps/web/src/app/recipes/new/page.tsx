"use client";

import Link from "next/link";
import { ArrowLeft, ArrowRight, Loader2, Sparkles } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  MIN_RECIPE_INPUT_LENGTH,
  type ProcessRecipeResponse,
  type ProcessRecipeSuccessResponse,
} from "@/lib/forkfolio-types";

type ErrorPayload = {
  detail?: string;
  error?: string;
};

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

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof BrowserApiError) {
    return error.detail ?? error.message;
  }
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

async function readErrorPayload(response: Response): Promise<ErrorPayload | null> {
  try {
    return (await response.json()) as ErrorPayload;
  } catch {
    return null;
  }
}

async function processRecipeClient(rawInput: string): Promise<ProcessRecipeResponse> {
  const response = await fetch("/api/recipes/process", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    cache: "no-store",
    body: JSON.stringify({
      raw_input: rawInput,
      enforce_deduplication: true,
      isTest: false,
    }),
  });

  if (!response.ok) {
    const payload = await readErrorPayload(response);
    const detail = payload?.detail ?? payload?.error ?? null;
    throw new BrowserApiError(
      detail ?? `Request failed with status ${response.status}.`,
      response.status,
      detail,
    );
  }

  return (await response.json()) as ProcessRecipeResponse;
}

function SuccessState({ result }: { result: ProcessRecipeSuccessResponse }) {
  const title = result.recipe.title?.trim() || "Recipe";
  const message = result.message?.trim()
    ? result.message
    : result.created
      ? "Recipe processed and stored successfully."
      : "Duplicate recipe found; returning existing recipe.";

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardHeader className="space-y-3">
        <Badge className="w-fit rounded-full px-3 py-0.5">
          {result.created ? "Created" : "Existing Recipe"}
        </Badge>
        <CardTitle className="font-display text-3xl leading-tight">{title}</CardTitle>
        <CardDescription className="text-base">{message}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="space-y-2">
          <p className="text-sm font-medium text-foreground/90">Recipe ID</p>
          <p className="rounded-lg border border-border/80 bg-background px-3 py-2 text-sm break-all">
            {result.recipe_id}
          </p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <Button asChild className="sm:flex-1">
            <Link href={`/recipes/${result.recipe_id}`}>
              Open Recipe
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" className="sm:flex-1">
            <Link href="/browse">Browse Recipes</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function NewRecipePage() {
  const [rawInput, setRawInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ProcessRecipeResponse | null>(null);

  const trimmedLength = useMemo(() => rawInput.trim().length, [rawInput]);
  const inputTooShort = trimmedLength < MIN_RECIPE_INPUT_LENGTH;

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedInput = rawInput.trim();
    if (normalizedInput.length < MIN_RECIPE_INPUT_LENGTH) {
      setErrorMessage(
        `Recipe input must be at least ${MIN_RECIPE_INPUT_LENGTH} characters.`,
      );
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    setResult(null);

    try {
      const response = await processRecipeClient(normalizedInput);
      setResult(response);
      if (!response.success) {
        setErrorMessage(response.error || "Recipe processing failed.");
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Recipe processing failed."));
    } finally {
      setIsSubmitting(false);
    }
  }

  const successfulResult = result?.success ? result : null;

  return (
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto w-full max-w-6xl px-4 py-10 sm:px-6">
        <Button asChild variant="ghost" className="mb-4">
          <Link href="/">
            <ArrowLeft className="size-4" />
            Back to Home
          </Link>
        </Button>

        <section className="rounded-[2rem] border border-border/70 bg-card/35 px-6 py-10 sm:px-10">
          <div className="mx-auto max-w-4xl space-y-8">
            <div className="space-y-3">
              <Badge variant="secondary" className="rounded-full px-3 py-0.5 text-xs">
                Add Recipe
              </Badge>
              <h1 className="font-display text-5xl tracking-tight sm:text-6xl">
                Turn raw text into a saved recipe
              </h1>
              <p className="text-lg text-muted-foreground">
                Paste unstructured recipe text and ForkFolio will clean, extract, and
                store it in your collection.
              </p>
            </div>

            <Card className="border-border/80 bg-background/80">
              <CardHeader className="space-y-2">
                <CardTitle className="font-display text-3xl">
                  Recipe Input
                </CardTitle>
                <CardDescription>
                  Include a title, ingredients, and instructions in plain text.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={onSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="raw_input">Raw recipe text</Label>
                    <Textarea
                      id="raw_input"
                      name="raw_input"
                      value={rawInput}
                      onChange={(event) => setRawInput(event.target.value)}
                      placeholder={
                        "Chocolate Chip Cookies\n\nIngredients:\n- 2 cups flour\n- 1 cup butter\n\nInstructions:\n1. Mix ingredients\n2. Bake at 350F"
                      }
                      className="min-h-56 resize-y"
                    />
                    <p className="text-sm text-muted-foreground">
                      {trimmedLength} characters
                      {inputTooShort
                        ? ` (${MIN_RECIPE_INPUT_LENGTH - trimmedLength} more needed)`
                        : ""}
                    </p>
                  </div>

                  <Button type="submit" size="lg" disabled={isSubmitting || inputTooShort}>
                    {isSubmitting ? (
                      <>
                        <Loader2 className="size-4 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="size-4" />
                        Process & Save Recipe
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </section>

        {errorMessage ? (
          <Card className="mt-6 border-destructive/35 bg-destructive/5">
            <CardHeader>
              <CardTitle>Unable to process recipe</CardTitle>
              <CardDescription>{errorMessage}</CardDescription>
            </CardHeader>
          </Card>
        ) : null}

        {successfulResult ? (
          <section className="mt-6">
            <SuccessState result={successfulResult} />
          </section>
        ) : null}
      </main>
    </div>
  );
}
