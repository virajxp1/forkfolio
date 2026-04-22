import { Clock3, Globe, LinkIcon, Lock, Users2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type RecipeMetadataBadgesProps = {
  servings?: string | null;
  totalTime?: string | null;
  sourceUrl?: string | null;
  isPublic?: boolean | null;
  showSourceUrl?: boolean;
  className?: string;
};

function normalizeText(value: string | null | undefined): string {
  return value?.trim() ?? "";
}

export function RecipeMetadataBadges({
  servings,
  totalTime,
  sourceUrl,
  isPublic,
  showSourceUrl = false,
  className,
}: RecipeMetadataBadgesProps) {
  const normalizedServings = normalizeText(servings);
  const normalizedTotalTime = normalizeText(totalTime);
  const normalizedSourceUrl = normalizeText(sourceUrl);
  const showAnyBadge =
    Boolean(normalizedServings) ||
    Boolean(normalizedTotalTime) ||
    typeof isPublic === "boolean" ||
    (showSourceUrl && Boolean(normalizedSourceUrl));

  if (!showAnyBadge) {
    return null;
  }

  return (
    <div className={cn("flex min-w-0 flex-wrap gap-2", className)}>
      {normalizedTotalTime ? (
        <Badge variant="secondary" className="min-w-0 max-w-full gap-1.5">
          <Clock3 className="size-3.5 shrink-0" />
          <span className="truncate">{normalizedTotalTime}</span>
        </Badge>
      ) : null}

      {normalizedServings ? (
        <Badge variant="secondary" className="min-w-0 max-w-full gap-1.5">
          <Users2 className="size-3.5 shrink-0" />
          <span className="truncate">{normalizedServings}</span>
        </Badge>
      ) : null}

      {typeof isPublic === "boolean" ? (
        <Badge variant="secondary" className="min-w-0 max-w-full gap-1.5">
          {isPublic ? (
            <Globe className="size-3.5 shrink-0" />
          ) : (
            <Lock className="size-3.5 shrink-0" />
          )}
          <span className="truncate">{isPublic ? "Public" : "Private"}</span>
        </Badge>
      ) : null}

      {showSourceUrl && normalizedSourceUrl ? (
        <Badge
          variant="outline"
          className="min-w-0 max-w-full gap-1.5 overflow-hidden"
          title={normalizedSourceUrl}
        >
          <LinkIcon className="size-3.5 shrink-0" />
          <span className="truncate">{normalizedSourceUrl}</span>
        </Badge>
      ) : null}
    </div>
  );
}
