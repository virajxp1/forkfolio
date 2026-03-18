"use client";

import Link from "next/link";
import { ArrowRight, Loader2, Sparkles } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  MIN_RECIPE_INPUT_LENGTH,
  type PreviewRecipeFromUrlResponse,
  type RecipePreviewRecord,
  type ProcessRecipeResponse,
  type ProcessRecipeSuccessResponse,
} from "@/lib/forkfolio-types";

type ErrorPayload = {
  detail?: string;
  error?: string;
};

type InputMode = "url" | "text";

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

async function processRecipeClient(
  rawInput: string,
  sourceUrl?: string,
): Promise<ProcessRecipeResponse> {
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
      ...(sourceUrl ? { source_url: sourceUrl } : {}),
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

async function previewRecipeFromUrlClient(
  sourceUrl: string,
): Promise<PreviewRecipeFromUrlResponse> {
  const response = await fetch("/api/recipes/preview", {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    cache: "no-store",
    body: JSON.stringify({
      url: sourceUrl,
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

  return (await response.json()) as PreviewRecipeFromUrlResponse;
}

function formatRecipePreviewAsRawInput(preview: RecipePreviewRecord): string {
  const ingredients = preview.ingredients
    .map((ingredient) => `- ${ingredient}`)
    .join("\n");
  const instructions = preview.instructions
    .map((instruction, index) => `${index + 1}. ${instruction}`)
    .join("\n");

  return [
    preview.title,
    "",
    `Servings: ${preview.servings}`,
    `Total time: ${preview.total_time}`,
    "",
    "Ingredients:",
    ingredients,
    "",
    "Instructions:",
    instructions,
  ].join("\n");
}

function SuccessState({
  result,
  onStartOver,
}: {
  result: ProcessRecipeSuccessResponse;
  onStartOver: () => void;
}) {
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
          <Button type="button" variant="outline" className="sm:flex-1" onClick={onStartOver}>
            Save Another Recipe
          </Button>
          <Button asChild variant="ghost" className="sm:flex-1">
            <Link href="/browse">Browse Recipes</Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function NewRecipePage() {
  const [rawInput, setRawInput] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [textModeSourceUrl, setTextModeSourceUrl] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<InputMode>("url");
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isSavingPreview, setIsSavingPreview] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [previewErrorMessage, setPreviewErrorMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [previewResult, setPreviewResult] = useState<PreviewRecipeFromUrlResponse | null>(
    null,
  );
  const [result, setResult] = useState<ProcessRecipeResponse | null>(null);

  const trimmedLength = useMemo(() => rawInput.trim().length, [rawInput]);
  const normalizedSourceUrl = useMemo(() => sourceUrl.trim(), [sourceUrl]);
  const inputTooShort = trimmedLength < MIN_RECIPE_INPUT_LENGTH;
  const sourceUrlInvalid = useMemo(() => {
    if (!normalizedSourceUrl) {
      return false;
    }
    try {
      const parsed = new URL(normalizedSourceUrl);
      return !["http:", "https:"].includes(parsed.protocol);
    } catch {
      return true;
    }
  }, [normalizedSourceUrl]);
  const canPreviewFromUrl = normalizedSourceUrl.length > 0 && !sourceUrlInvalid;

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
    setPreviewErrorMessage(null);
    setResult(null);

    try {
      const response = await processRecipeClient(
        normalizedInput,
        textModeSourceUrl ?? undefined,
      );
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

  async function onPreviewSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canPreviewFromUrl) {
      setPreviewErrorMessage("Enter a valid http or https URL.");
      return;
    }

    setIsPreviewing(true);
    setPreviewErrorMessage(null);
    setErrorMessage(null);
    setPreviewResult(null);
    setTextModeSourceUrl(null);

    try {
      const response = await previewRecipeFromUrlClient(normalizedSourceUrl);
      setPreviewResult(response);
      if (!response.success) {
        setPreviewErrorMessage(response.error || "Recipe preview failed.");
      }
    } catch (error) {
      setPreviewErrorMessage(
        getErrorMessage(error, "Failed to fetch recipe preview from URL."),
      );
    } finally {
      setIsPreviewing(false);
    }
  }

  async function savePreviewRecipe(preview: RecipePreviewRecord, sourceUrlForSave: string) {
    const normalizedInput = formatRecipePreviewAsRawInput(preview);

    setIsSavingPreview(true);
    setErrorMessage(null);
    setResult(null);

    try {
      const response = await processRecipeClient(normalizedInput, sourceUrlForSave);
      setResult(response);
      if (response.success) {
        setPreviewResult(null);
        setSourceUrl("");
        setTextModeSourceUrl(null);
      } else {
        setErrorMessage(response.error || "Recipe processing failed.");
      }
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Recipe processing failed."));
    } finally {
      setIsSavingPreview(false);
    }
  }

  function applyPreviewAsText(preview: RecipePreviewRecord, sourceUrlForSave: string) {
    setRawInput(formatRecipePreviewAsRawInput(preview));
    setInputMode("text");
    setTextModeSourceUrl(sourceUrlForSave);
    setPreviewErrorMessage(null);
  }

  function resetComposer() {
    setRawInput("");
    setSourceUrl("");
    setInputMode("url");
    setTextModeSourceUrl(null);
    setIsPreviewing(false);
    setIsSavingPreview(false);
    setIsSubmitting(false);
    setPreviewErrorMessage(null);
    setErrorMessage(null);
    setPreviewResult(null);
    setResult(null);
  }

  const successfulResult = result?.success ? result : null;
  const successfulPreview = previewResult?.success ? previewResult : null;
  const previewIngredients = successfulPreview
    ? successfulPreview.recipe_preview.ingredients.slice(0, 8)
    : [];
  const previewInstructions = successfulPreview
    ? successfulPreview.recipe_preview.instructions.slice(0, 8)
    : [];
  const additionalIngredientCount = successfulPreview
    ? Math.max(0, successfulPreview.recipe_preview.ingredients.length - previewIngredients.length)
    : 0;
  const additionalInstructionCount = successfulPreview
    ? Math.max(0, successfulPreview.recipe_preview.instructions.length - previewInstructions.length)
    : 0;

  return (
    <PageShell>
      <ForkfolioHeader />

      <PageMain className="space-y-8 ff-animate-enter">
        <PageBackLink href="/" label="Back to Home" />

        {successfulResult ? (
          <PageHero
            badge="Recipe Saved"
            title="Recipe saved successfully"
            description="Open the saved recipe, browse your collection, or start another import."
            contentClassName="max-w-4xl"
          >
            <SuccessState result={successfulResult} onStartOver={resetComposer} />
          </PageHero>
        ) : (
          <PageHero
            badge="Add Recipe"
            title="Turn raw text into a saved recipe"
            description="Import from a URL or paste plain text. Use one path at a time for a cleaner save flow."
            contentClassName="max-w-4xl"
          >
              <Tabs
                value={inputMode}
                onValueChange={(value) => {
                  setInputMode(value as InputMode);
                  setTextModeSourceUrl(null);
                }}
                className="space-y-4"
              >
                <TabsList className="grid w-full grid-cols-2" variant="default">
                  <TabsTrigger value="url">Import URL</TabsTrigger>
                  <TabsTrigger value="text">Paste Text</TabsTrigger>
                </TabsList>

                <TabsContent value="url">
                  <Card className="border-border/80 bg-background/82 shadow-none">
                    <CardHeader className="space-y-2">
                      <CardTitle className="font-display text-3xl">
                        Import From URL
                      </CardTitle>
                      <CardDescription>
                        Fetch a webpage, preview extracted recipe fields, then save the
                        recipe directly.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <form onSubmit={onPreviewSubmit} className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="source_url">Recipe URL</Label>
                          <Input
                            id="source_url"
                            name="source_url"
                            type="url"
                            value={sourceUrl}
                            onChange={(event) => setSourceUrl(event.target.value)}
                            placeholder="https://example.com/chocolate-chip-cookies"
                            className="border-border/80 bg-background/80"
                          />
                          <p className="text-sm text-muted-foreground">
                            Preview alone does not insert into your database until you save.
                          </p>
                        </div>

                        <Button
                          type="submit"
                          variant="secondary"
                          disabled={isPreviewing || !canPreviewFromUrl}
                        >
                          {isPreviewing ? (
                            <>
                              <Loader2 className="size-4 animate-spin" />
                              Fetching Preview...
                            </>
                          ) : (
                            <>
                              <Sparkles className="size-4" />
                              Fetch URL Preview
                            </>
                          )}
                        </Button>
                      </form>

                      {previewErrorMessage ? (
                        <p className="text-sm text-destructive">{previewErrorMessage}</p>
                      ) : null}

                      {successfulPreview ? (
                        <Card className="border-primary/30 bg-primary/5">
                          <CardHeader className="space-y-2">
                            <Badge className="w-fit rounded-full px-3 py-0.5">Preview</Badge>
                            <CardTitle className="font-display text-2xl leading-tight">
                              {successfulPreview.recipe_preview.title}
                            </CardTitle>
                            <CardDescription className="text-sm">
                              Servings: {successfulPreview.recipe_preview.servings} | Total
                              time: {successfulPreview.recipe_preview.total_time}
                            </CardDescription>
                          </CardHeader>
                          <CardContent className="space-y-5">
                            <div className="grid gap-5 md:grid-cols-2">
                              <div className="space-y-2">
                                <p className="text-sm font-medium text-foreground/90">
                                  Ingredients
                                </p>
                                <ul className="list-disc space-y-1 pl-5 text-sm text-foreground/90">
                                  {previewIngredients.map((ingredient, index) => (
                                    <li key={`${ingredient}-${index}`}>{ingredient}</li>
                                  ))}
                                  {additionalIngredientCount > 0 ? (
                                    <li className="text-muted-foreground">
                                      +{additionalIngredientCount} more
                                    </li>
                                  ) : null}
                                </ul>
                              </div>

                              <div className="space-y-2">
                                <p className="text-sm font-medium text-foreground/90">
                                  Instructions
                                </p>
                                <ol className="list-decimal space-y-1 pl-5 text-sm text-foreground/90">
                                  {previewInstructions.map((instruction, index) => (
                                    <li key={`${instruction}-${index}`}>{instruction}</li>
                                  ))}
                                  {additionalInstructionCount > 0 ? (
                                    <li className="text-muted-foreground">
                                      +{additionalInstructionCount} more
                                    </li>
                                  ) : null}
                                </ol>
                              </div>
                            </div>

                            <div className="flex flex-col gap-2 sm:flex-row">
                              <Button
                                type="button"
                                variant="outline"
                                onClick={() =>
                                  void savePreviewRecipe(
                                    successfulPreview.recipe_preview,
                                    successfulPreview.url,
                                  )
                                }
                                disabled={isSavingPreview}
                              >
                                {isSavingPreview ? (
                                  <>
                                    <Loader2 className="size-4 animate-spin" />
                                    Saving...
                                  </>
                                ) : (
                                  "Save Recipe"
                                )}
                              </Button>
                              <Button
                                type="button"
                                variant="ghost"
                                disabled={isSavingPreview}
                                onClick={() =>
                                  applyPreviewAsText(
                                    successfulPreview.recipe_preview,
                                    successfulPreview.url,
                                  )
                                }
                              >
                                Edit As Text
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ) : null}
                    </CardContent>
                  </Card>
                </TabsContent>

                <TabsContent value="text">
                  <Card className="border-border/80 bg-background/82 shadow-none">
                    <CardHeader className="space-y-2">
                      <CardTitle className="font-display text-3xl">Recipe Input</CardTitle>
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
                            className="min-h-56 resize-y border-border/80 bg-background/80"
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
                </TabsContent>
              </Tabs>
          </PageHero>
        )}

        {errorMessage ? (
          <Card className="border-destructive/35 bg-destructive/5 shadow-none">
            <CardHeader>
              <CardTitle>Unable to process recipe</CardTitle>
              <CardDescription>{errorMessage}</CardDescription>
            </CardHeader>
          </Card>
        ) : null}
      </PageMain>
    </PageShell>
  );
}
