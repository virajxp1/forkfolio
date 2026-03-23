import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type RecipeContentColumnsProps = {
  ingredients: string[];
  instructions: string[];
  className?: string;
  cardClassName?: string;
};

function cleanLines(lines: string[]): string[] {
  return lines
    .map((line) => line.trim())
    .filter((line) => Boolean(line));
}

export function RecipeContentColumns({
  ingredients,
  instructions,
  className,
  cardClassName,
}: RecipeContentColumnsProps) {
  const ingredientLines = cleanLines(ingredients);
  const instructionLines = cleanLines(instructions);

  return (
    <div className={cn("grid grid-cols-1 gap-5 lg:grid-cols-[1fr_1.3fr]", className)}>
      <Card className={cn("border-border/80 bg-background/80 shadow-none", cardClassName)}>
        <CardHeader>
          <CardTitle className="font-display text-3xl">Ingredients</CardTitle>
          <CardDescription>
            {ingredientLines.length} item{ingredientLines.length === 1 ? "" : "s"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {ingredientLines.length ? (
            <ul className="space-y-2">
              {ingredientLines.map((ingredient, index) => (
                <li key={`${ingredient}-${index}`} className="break-words text-foreground/90">
                  • {ingredient}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              No ingredients are listed for this recipe yet.
            </p>
          )}
        </CardContent>
      </Card>

      <Card className={cn("border-border/80 bg-background/80 shadow-none", cardClassName)}>
        <CardHeader>
          <CardTitle className="font-display text-3xl">Instructions</CardTitle>
          <CardDescription>
            {instructionLines.length} step{instructionLines.length === 1 ? "" : "s"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {instructionLines.length ? (
            <ol className="space-y-3">
              {instructionLines.map((instruction, index) => (
                <li key={`${instruction}-${index}`} className="flex items-start gap-3">
                  <span className="inline-flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                    {index + 1}
                  </span>
                  <p className="break-words pt-0.5 text-foreground/90">{instruction}</p>
                </li>
              ))}
            </ol>
          ) : (
            <p className="text-sm text-muted-foreground">
              No instructions are listed for this recipe yet.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
