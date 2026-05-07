"use client";

import { Check, ShoppingBag } from "lucide-react";
import { MouseEvent } from "react";

import { useGroceryBag } from "@/components/grocery-bag-provider";
import { Button } from "@/components/ui/button";
import type { GroceryBagRecipe } from "@/lib/forkfolio-types";

type RecipeBagToggleButtonProps = {
  recipe: GroceryBagRecipe;
  size?: "sm" | "default" | "lg" | "icon";
  className?: string;
};

export function RecipeBagToggleButton({
  recipe,
  size = "sm",
  className,
}: RecipeBagToggleButtonProps) {
  const { hasRecipe, addRecipe, removeRecipe } = useGroceryBag();
  const isInBag = hasRecipe(recipe.id);

  function onClick(event: MouseEvent<HTMLButtonElement>) {
    // Keep parent card interactions intact when this button sits inside clickable surfaces.
    event.stopPropagation();

    if (isInBag) {
      removeRecipe(recipe.id);
      return;
    }
    addRecipe(recipe);
  }

  return (
    <Button
      type="button"
      variant={isInBag ? "outline" : "secondary"}
      size={size}
      className={className}
      onClick={onClick}
      aria-pressed={isInBag}
    >
      {isInBag ? <Check className="size-4" /> : <ShoppingBag className="size-4" />}
      {isInBag ? "In Bag" : "Add to Bag"}
    </Button>
  );
}
