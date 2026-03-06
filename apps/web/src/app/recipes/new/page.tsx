"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
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
import { MIN_RECIPE_INPUT_LENGTH } from "@/lib/forkfolio-types";

type ProcessApiResponse = {
  recipe_id?: string;
  success?: boolean;
  message?: string;
  detail?: string;
  error?: string;
};

function getPayloadMessage(payload: ProcessApiResponse | null, fallback: string): string {
  if (!payload) {
    return fallback;
  }

  if (typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }
  if (typeof payload.error === "string" && payload.error.trim()) {
    return payload.error;
  }
  if (typeof payload.message === "string" && payload.message.trim()) {
    return payload.message;
  }

  return fallback;
}

async function readPayload(response: Response): Promise<ProcessApiResponse | null> {
  try {
    return (await response.json()) as ProcessApiResponse;
  } catch {
    return null;
  }
}

export default function NewRecipePage() {
  const [rawInput, setRawInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [successPayload, setSuccessPayload] = useState<ProcessApiResponse | null>(null);

  const inputLength = rawInput.trim().length;

  const helperText = useMemo(() => {
    if (!rawInput.trim()) {
      return `Paste at least ${MIN_RECIPE_INPUT_LENGTH} characters of recipe text.`;
    }
    if (inputLength < MIN_RECIPE_INPUT_LENGTH) {
      return `${MIN_RECIPE_INPUT_LENGTH - inputLength} more character${
        MIN_RECIPE_INPUT_LENGTH - inputLength === 1 ? "" : "s"
      } needed.`;
    }
    return "Ready to process.";
  }, [rawInput, inputLength]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedInput = rawInput.trim();
    setValidationError(null);
    setSubmitError(null);
    setSuccessPayload(null);

    if (normalizedInput.length < MIN_RECIPE_INPUT_LENGTH) {
      setValidationError(
        `Recipe text must be at least ${MIN_RECIPE_INPUT_LENGTH} characters long.`,
      );
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch("/api/recipes/process", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ raw_input: normalizedInput }),
      });

      const payload = await readPayload(response);

      if (!response.ok) {
        setSubmitError(getPayloadMessage(payload, "Failed to process recipe."));
        return;
      }

      if (payload?.success === false) {
        setSubmitError(getPayloadMessage(payload, "Recipe processing failed."));
        return;
      }

      setSuccessPayload(payload ?? { success: true });
      setRawInput("");
    } catch {
      setSubmitError("Failed to process recipe.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const successMessage = successPayload
    ? getPayloadMessage(successPayload, "Recipe processed successfully.")
    : null;
  const savedRecipeId =
    typeof successPayload?.recipe_id === "string" && successPayload.recipe_id.trim()
      ? successPayload.recipe_id.trim()
      : null;

  return (
    <div className="min-h-screen">
      <ForkfolioHeader />

      <main className="mx-auto w-full max-w-5xl px-4 py-10 sm:px-6">
        <section className="rounded-[2rem] border border-border/70 bg-card/35 px-6 py-10 sm:px-10">
          <div className="mx-auto max-w-4xl space-y-6">
            <div className="space-y-2">
              <Badge variant="secondary" className="rounded-full px-3 py-0.5 text-xs">
                Add Recipe
              </Badge>
              <h1 className="font-display text-5xl tracking-tight sm:text-6xl">
                Process a new recipe
              </h1>
              <p className="text-lg text-muted-foreground">
                Paste raw recipe text and ForkFolio will extract ingredients and
                instructions.
              </p>
            </div>

            <Card>
              <CardHeader>
                <CardTitle className="font-display text-3xl">Recipe input</CardTitle>
                <CardDescription>
                  Include title, ingredients, and steps when possible.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={onSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="raw-input">Raw recipe text</Label>
                    <Textarea
                      id="raw-input"
                      name="raw_input"
                      placeholder="Paste recipe text from a note, website, or document..."
                      value={rawInput}
                      onChange={(event) => {
                        setRawInput(event.target.value);
                        if (validationError) {
                          setValidationError(null);
                        }
                      }}
                      rows={12}
                      className="rounded-xl bg-background"
                    />
                    <p className="text-sm text-muted-foreground">{helperText}</p>
                  </div>

                  <Button type="submit" size="lg" disabled={isSubmitting}>
                    <Sparkles className="size-4" />
                    {isSubmitting ? "Processing..." : "Process Recipe"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {validationError ? (
              <Card className="border-destructive/35 bg-destructive/5">
                <CardHeader>
                  <CardTitle>Validation Error</CardTitle>
                  <CardDescription>{validationError}</CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {submitError ? (
              <Card className="border-destructive/35 bg-destructive/5">
                <CardHeader>
                  <CardTitle>Unable to process recipe</CardTitle>
                  <CardDescription>{submitError}</CardDescription>
                </CardHeader>
              </Card>
            ) : null}

            {successMessage ? (
              <Card className="border-primary/35 bg-primary/5">
                <CardHeader>
                  <CardTitle>Recipe saved</CardTitle>
                  <CardDescription>{successMessage}</CardDescription>
                </CardHeader>
                {savedRecipeId ? (
                  <CardContent>
                    <Button asChild variant="outline">
                      <Link href={`/recipes/${savedRecipeId}`}>
                        View recipe details
                        <ArrowRight className="size-4" />
                      </Link>
                    </Button>
                  </CardContent>
                ) : null}
              </Card>
            ) : null}
          </div>
        </section>
      </main>
    </div>
  );
}
